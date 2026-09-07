#include <array>
#include <atomic>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <time.h>

#include <absl/base/internal/cycleclock.h>
#include <absl/base/internal/sysinfo.h>
#include <absl/synchronization/mutex.h>
#include <absl/synchronization/notification.h>
#include <absl/time/clock.h>
#include <absl/time/time.h>

namespace {

void stage(const char *name) { std::printf("V8-ABSEIL: START %s\n", name); }
bool fail(const char *name)
{
    std::fprintf(stderr, "V8-ABSEIL: FAIL %s\n", name);
    return false;
}

int64_t monotonic_ns()
{
    timespec value{};
    if (clock_gettime(CLOCK_MONOTONIC, &value) || value.tv_sec < 0 ||
        value.tv_nsec < 0 || value.tv_nsec >= 1000000000) return -1;
    return int64_t(value.tv_sec) * 1000000000 + value.tv_nsec;
}

bool pause_ms(long milliseconds)
{
    timespec remaining{milliseconds / 1000, (milliseconds % 1000) * 1000000};
    while (nanosleep(&remaining, &remaining)) {
        if (errno != EINTR) return fail("nanosleep");
    }
    return true;
}

bool clocks()
{
    stage("nominal-cpu-frequency");
    const double nominal = absl::base_internal::NominalCPUFrequency();
    if (!std::isfinite(nominal) || nominal <= 0) return fail("nominal frequency");
    stage("cycle-clock-frequency");
    const double frequency = absl::base_internal::CycleClock::Frequency();
    if (!std::isfinite(frequency) || frequency <= 0) return fail("cycle frequency");
    stage("monotonic-clock");
    const int64_t before = monotonic_ns();
    const int64_t cycles = absl::base_internal::CycleClock::Now();
    if (before < 0 || !pause_ms(25)) return fail("clock read or sleep");
    const int64_t after = monotonic_ns();
    if (after <= before) return fail("monotonic clock did not advance");
    std::printf("V8-ABSEIL: clocks nominal=%.0f cycle=%.0f elapsed_ns=%lld cycles=%lld\n",
                nominal, frequency, static_cast<long long>(after - before),
                static_cast<long long>(absl::base_internal::CycleClock::Now() - cycles));
    return true;
}

bool notification()
{
    stage("notification-untimed");
    absl::Notification event;
    std::atomic<bool> entering{false}, returned{false};
    std::atomic<int> payload{0};
    int observed = 0;
    std::thread waiter([&] {
        entering.store(true, std::memory_order_release);
        event.WaitForNotification();
        observed = payload.load(std::memory_order_relaxed);
        returned.store(true, std::memory_order_release);
    });
    while (!entering.load(std::memory_order_acquire)) std::this_thread::yield();
    const bool slept = pause_ms(50);
    const bool premature = returned.load(std::memory_order_acquire);
    payload.store(42, std::memory_order_relaxed);
    stage("notification-notify");
    event.Notify();
    waiter.join();
    if (!slept || premature || observed != 42 || !event.HasBeenNotified()) {
        return fail("notification wakeup or visibility");
    }

    absl::Notification absent;
    stage("notification-timeout");
    int64_t before = monotonic_ns();
    bool signalled = absent.WaitForNotificationWithTimeout(absl::Milliseconds(100));
    int64_t after = monotonic_ns();
    // Allow one coarse 10 ms clock tick when comparing different clock sources.
    if (before < 0 || after < before || signalled || after - before < 90000000) {
        return fail("notification timeout returned prematurely");
    }
    std::printf("V8-ABSEIL: timeout elapsed_ns=%lld\n",
                static_cast<long long>(after - before));
    stage("notification-deadline");
    before = monotonic_ns();
    const absl::Time deadline = absl::Now() + absl::Milliseconds(100);
    signalled = absent.WaitForNotificationWithDeadline(deadline);
    after = monotonic_ns();
    if (before < 0 || after < before || signalled || after - before < 90000000 ||
        absl::Now() < deadline) return fail("notification deadline returned prematurely");
    std::printf("V8-ABSEIL: deadline elapsed_ns=%lld\n",
                static_cast<long long>(after - before));
    stage("notification-already-notified");
    if (!event.WaitForNotificationWithTimeout(absl::ZeroDuration()) ||
        !event.WaitForNotificationWithDeadline(absl::InfinitePast())) {
        return fail("notified state lost");
    }
    return true;
}

bool mutex_and_threads()
{
    stage("mutex-contended-and-thread-ids");
    absl::Mutex mutex;
    std::atomic<unsigned> ready{0};
    std::array<pid_t, 4> ids{};
    std::array<std::thread, 4> workers;
    uint64_t count = 0, mirror = 0;
    bool consistent = true;
    mutex.Lock();
    for (size_t worker = 0; worker < workers.size(); ++worker) {
        workers[worker] = std::thread([&, worker] {
            ids[worker] = absl::base_internal::GetTID();
            ready.fetch_add(1, std::memory_order_acq_rel);
            for (unsigned i = 0; i < 2000; ++i) {
                absl::MutexLock held(&mutex);
                if (mirror != count * 3) consistent = false;
                ++count;
                mirror = count * 3;
                if ((i % 128) == 0) std::this_thread::yield();
            }
        });
    }
    while (ready.load(std::memory_order_acquire) != workers.size()) {
        std::this_thread::yield();
    }
    bool distinct = true;
    const pid_t main_id = absl::base_internal::GetTID();
    for (size_t i = 0; i < ids.size(); ++i) {
        if (ids[i] <= 0 || ids[i] == main_id) distinct = false;
        for (size_t j = 0; j < i; ++j) if (ids[i] == ids[j]) distinct = false;
    }
    const bool slept = pause_ms(25);
    stage("mutex-release-and-join");
    mutex.Unlock();
    for (auto &worker : workers) worker.join();
    if (!slept || !distinct || !consistent || count != 8000 || mirror != 24000) {
        return fail("mutex exclusion, visibility, or live thread IDs");
    }
    std::printf("V8-ABSEIL: mutex count=%llu tids=%ld,%ld,%ld,%ld\n",
                static_cast<unsigned long long>(count), static_cast<long>(ids[0]),
                static_cast<long>(ids[1]), static_cast<long>(ids[2]), static_cast<long>(ids[3]));
    return true;
}

}  // namespace

int main()
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    if (!clocks() || !notification() || !mutex_and_threads()) return 1;
    std::puts("V8-ABSEIL: PASS clocks notifications mutex threads");
    return 0;
}
