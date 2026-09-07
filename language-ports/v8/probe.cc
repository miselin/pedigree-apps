#include <atomic>
#include <cstdio>
#include <cstring>
#include <memory>
#include <string_view>

#include <libplatform/libplatform.h>
#include <v8.h>

static_assert(v8::Promise::kEmbedderFieldCount == 1);

namespace {

struct ProbeState {
    int callback_calls = 0;
    int callback_value = 0;
    unsigned collections = 0;
    std::atomic<bool> generated_code = false;
};

bool fail(const char *check)
{
    std::fprintf(stderr, "V8-QUALIFY: FAIL %s\n", check);
    return false;
}

void host_record(const v8::FunctionCallbackInfo<v8::Value> &args)
{
    if (args.Length() != 1 || !args[0]->IsInt32()) {
        args.GetIsolate()->ThrowException(v8::Exception::TypeError(
            v8::String::NewFromUtf8Literal(args.GetIsolate(), "expected integer")));
        return;
    }
    auto *state = static_cast<ProbeState *>(args.GetIsolate()->GetData(0));
    ++state->callback_calls;
    state->callback_value = args[0].As<v8::Int32>()->Value();
    args.GetReturnValue().Set(state->callback_value * 2);
}

void code_event(const v8::JitCodeEvent *event)
{
    if (event->type == v8::JitCodeEvent::CODE_ADDED &&
        event->code_type == v8::JitCodeEvent::JIT_CODE && event->code_len &&
        std::string_view(event->name.str, event->name.len).find("pedigreeJitProbe") !=
            std::string_view::npos) {
        auto *state = static_cast<ProbeState *>(event->isolate->GetData(0));
        state->generated_code.store(true);
    }
}

void collected(v8::Isolate *, v8::GCType, v8::GCCallbackFlags, void *data)
{
    ++static_cast<ProbeState *>(data)->collections;
}

bool check_script(v8::Local<v8::Context> context, const char *name, const char *source)
{
    auto *isolate = context->GetIsolate();
    v8::HandleScope handles(isolate);
    v8::TryCatch caught(isolate);
    v8::Local<v8::String> text;
    v8::Local<v8::Script> script;
    v8::Local<v8::Value> result;
    if (!v8::String::NewFromUtf8(isolate, source).ToLocal(&text) ||
        !v8::Script::Compile(context, text).ToLocal(&script) ||
        !script->Run(context).ToLocal(&result)) {
        if (caught.HasCaught()) {
            v8::String::Utf8Value message(isolate, caught.Exception());
            std::fprintf(stderr, "V8-QUALIFY: exception: %s\n",
                         *message ? *message : "unavailable");
        }
        return fail(name);
    }
    return result->IsTrue() || fail(name);
}

bool check_exception(v8::Local<v8::Context> context)
{
    auto *isolate = context->GetIsolate();
    v8::HandleScope handles(isolate);
    v8::TryCatch caught(isolate);
    auto source = v8::String::NewFromUtf8Literal(
        isolate, "throw new Error('expected qualification exception')");
    v8::Local<v8::Script> script;
    if (!v8::Script::Compile(context, source).ToLocal(&script)) {
        return fail("exception compilation");
    }
    if (!script->Run(context).IsEmpty() || !caught.HasCaught()) {
        return fail("exception propagation");
    }
    v8::String::Utf8Value message(isolate, caught.Exception());
    if (!*message || !std::strstr(*message, "expected qualification exception")) {
        return fail("exception contents");
    }
    caught.Reset();
    return check_script(context, "exception recovery", "40 + 2 === 42");
}

bool run_checks(v8::Local<v8::Context> context, ProbeState &state, bool jit)
{
    auto *isolate = context->GetIsolate();
    if (!check_script(context, "arithmetic", "6 * 7 === 42") ||
        !check_script(context, "language", R"JS(
            (() => {
                class Counter { #value = 40; next() { return ++this.#value; } }
                const counter = new Counter();
                const values = new Map([['answer', counter.next() + 1]]);
                return values.get('answer') === 42 &&
                    new Set([1, 1, 2]).size === 2 &&
                    (2n ** 64n).toString() === '18446744073709551616' &&
                    [...'\u{1f680}'].length === 1;
            })()
        )JS") ||
        !check_script(context, "array buffers", R"JS(
            (() => {
                const buffer = new ArrayBuffer(65536);
                const bytes = new Uint8Array(buffer);
                bytes.fill(7);
                const view = new DataView(buffer);
                view.setUint32(0, 0x12345678, true);
                return bytes[0] === 0x78 && bytes[3] === 0x12 &&
                    bytes[65535] === 7 && view.getUint32(0, true) === 0x12345678;
            })()
        )JS") ||
        !check_script(context, "host callback", "hostRecord(21) === 42")) {
        return false;
    }
    if (state.callback_calls != 1 || state.callback_value != 21) {
        return fail("host callback state");
    }
    if (!check_script(context, "promise scheduling", R"JS(
            Promise.resolve(40).then(value => hostRecord(value + 2)); true
        )JS")) {
        return false;
    }
    if (state.callback_calls != 1) {
        return fail("explicit microtask policy");
    }
    isolate->PerformMicrotaskCheckpoint();
    if (state.callback_calls != 2 || state.callback_value != 42) {
        return fail("promise microtask callback");
    }
    if (!check_exception(context) ||
        !check_script(context, "heap allocation", R"JS(
            (() => {
                const objects = Array.from({length: 10000}, (_, i) => ({value: i}));
                return objects.reduce((sum, item) => sum + item.value, 0) === 49995000;
            })()
        )JS")) {
        return false;
    }
    const unsigned before = state.collections;
    isolate->LowMemoryNotification();
    if (state.collections <= before) {
        return fail("garbage collection callback");
    }
    if (!check_script(context, "execution after collection", "hostRecord(22) === 44") ||
        !check_script(context, "compiled function", R"JS(
            function pedigreeJitProbe(value) { return (value * 3 + 7) | 0; }
            (() => {
                let sum = 0;
                for (let i = 0; i < 4096; ++i) sum += pedigreeJitProbe(i);
                return sum === 25188352;
            })()
        )JS")) {
        return false;
    }
    return state.generated_code.load() == jit || fail("JIT code event");
}

bool run_isolate(bool jit, bool default_range)
{
    ProbeState state;
    std::unique_ptr<v8::ArrayBuffer::Allocator> allocator(
        v8::ArrayBuffer::Allocator::NewDefaultAllocator());
    v8::Isolate::CreateParams params;
    params.array_buffer_allocator = allocator.get();
    params.constraints.ConfigureDefaultsFromHeapSize(0, 64 * 1024 * 1024);
    // Heap defaults also set the code range; zero selects the port's own default.
    params.constraints.set_code_range_size_in_bytes(default_range ? 0 : 64 * 1024 * 1024);
    auto *isolate = v8::Isolate::New(params);
    if (!isolate) {
        return fail("isolate initialization");
    }
    void *code_start = nullptr;
    size_t code_size = 0;
    isolate->GetCodeRange(&code_start, &code_size);
    const size_t expected_size = (default_range ? 512u : 64u) * 1024 * 1024;
    if (!code_start || code_size != expected_size) {
        std::fprintf(stderr, "V8-QUALIFY: code range %zu bytes, expected %zu\n",
                     code_size, expected_size);
        isolate->Dispose();
        return fail("code range size");
    }
    isolate->SetData(0, &state);
    isolate->SetMicrotasksPolicy(v8::MicrotasksPolicy::kExplicit);
    isolate->SetJitCodeEventHandler(v8::kJitCodeEventDefault, code_event);
    isolate->AddGCEpilogueCallback(collected, &state);
    bool success;
    {
        v8::Isolate::Scope entered(isolate);
        v8::HandleScope handles(isolate);
        auto global = v8::ObjectTemplate::New(isolate);
        global->Set(isolate, "hostRecord", v8::FunctionTemplate::New(isolate, host_record));
        auto context = v8::Context::New(isolate, nullptr, global);
        v8::Context::Scope entered_context(context);
        success = run_checks(context, state, jit);
    }
    isolate->RemoveGCEpilogueCallback(collected, &state);
    isolate->SetJitCodeEventHandler(v8::kJitCodeEventDefault, nullptr);
    isolate->Dispose();
    return success;
}

}  // namespace

int main(int argc, char **argv)
{
    if (argc != 2 || (std::strcmp(argv[1], "jitless") && std::strcmp(argv[1], "jit") &&
                      std::strcmp(argv[1], "jit-default"))) {
        std::fprintf(stderr, "Usage: v8-qualify jitless|jit|jit-default\n");
        return 2;
    }
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    const bool jit = std::strcmp(argv[1], "jitless") != 0;
    const bool default_range = !std::strcmp(argv[1], "jit-default");
    // Leave native call frames room within Pedigree's 1 MiB thread stack.
    v8::V8::SetFlagsFromString("--stack-size=512");
    // Force synchronous baseline compilation so code events prove generated code.
    v8::V8::SetFlagsFromString(jit ? "--always-sparkplug --no-concurrent-sparkplug "
                                    "--no-concurrent-recompilation"
                                  : "--jitless");
    auto platform = v8::platform::NewDefaultPlatform(1);
    v8::V8::InitializePlatform(platform.get());
    if (!v8::V8::Initialize()) {
        fail("V8 initialization");
        v8::V8::DisposePlatform();
        return 1;
    }
    std::printf("V8-QUALIFY: START %s (%s)\n", argv[1], v8::V8::GetVersion());
    bool success = run_isolate(jit, default_range);
    if (success) {
        std::puts("V8-QUALIFY: first isolate disposed");
        success = run_isolate(jit, default_range);
    }
    if (!v8::V8::Dispose()) {
        success = fail("V8 disposal");
    }
    v8::V8::DisposePlatform();
    platform.reset();
    if (!success) {
        return 1;
    }
    std::printf("V8-QUALIFY: PASS %s (2 isolates)\n", argv[1]);
    return 0;
}
