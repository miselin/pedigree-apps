package main

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sync"
	"time"
)

func scheduler() error {
	const workers = 8
	results := make(chan uint64, workers)
	var group sync.WaitGroup
	for worker := 0; worker < workers; worker++ {
		group.Add(1)
		go func() {
			defer group.Done()
			data := make([]byte, 1<<20)
			var sum uint64
			for i := range data {
				data[i] = byte(i)
				sum += uint64(data[i])
			}
			runtime.Gosched()
			results <- sum
		}()
	}
	group.Wait()
	close(results)
	for sum := range results {
		if sum != 133693440 {
			return fmt.Errorf("bad heap checksum: %d", sum)
		}
	}
	runtime.GC()
	return nil
}

func files() error {
	dir, err := os.MkdirTemp("", "go-qualify-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(dir)
	path := filepath.Join(dir, "data")
	payload := bytes.Repeat([]byte("Pedigree Go\n"), 1024)
	if err = os.WriteFile(path, payload, 0600); err != nil {
		return err
	}
	if err = os.Rename(path, path+".renamed"); err != nil {
		return err
	}
	if err = os.Symlink("data.renamed", path); err != nil {
		return err
	}
	got, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	if !bytes.Equal(got, payload) {
		return fmt.Errorf("file contents differ")
	}
	entries, err := os.ReadDir(dir)
	if err != nil || len(entries) != 2 {
		return fmt.Errorf("directory entries=%d: %v", len(entries), err)
	}
	return os.Truncate(path, 7)
}

func timer() error {
	start := time.Now()
	<-time.After(20 * time.Millisecond)
	if elapsed := time.Since(start); elapsed < 10*time.Millisecond {
		return fmt.Errorf("timer returned early: %s", elapsed)
	}
	return nil
}

func pipe() error {
	reader, writer, err := os.Pipe()
	if err != nil {
		return err
	}
	defer reader.Close()
	done := make(chan error, 1)
	go func() {
		_, err := io.WriteString(writer, "pipe payload")
		writer.Close()
		done <- err
	}()
	got, err := io.ReadAll(reader)
	if err != nil {
		return err
	}
	if string(got) != "pipe payload" {
		return fmt.Errorf("pipe returned %q", got)
	}
	return <-done
}

func network(network, address string) error {
	listener, err := net.Listen(network, address)
	if err != nil {
		return err
	}
	defer listener.Close()
	if unix, ok := listener.(*net.UnixListener); ok {
		unix.SetDeadline(time.Now().Add(5 * time.Second))
	} else {
		listener.(*net.TCPListener).SetDeadline(time.Now().Add(5 * time.Second))
	}
	done := make(chan error, 1)
	go func() {
		conn, err := listener.Accept()
		if err == nil {
			defer conn.Close()
			conn.SetDeadline(time.Now().Add(5 * time.Second))
			_, err = io.CopyN(conn, conn, 12)
		}
		done <- err
	}()
	conn, err := net.DialTimeout(network, listener.Addr().String(), 5*time.Second)
	if err != nil {
		return err
	}
	defer conn.Close()
	if err = conn.SetDeadline(time.Now().Add(5 * time.Second)); err != nil {
		return err
	}
	if _, err = io.WriteString(conn, "network echo"); err != nil {
		return err
	}
	got := make([]byte, 12)
	if _, err = io.ReadFull(conn, got); err != nil {
		return err
	}
	if string(got) != "network echo" {
		return fmt.Errorf("echo returned %q", got)
	}
	return <-done
}

func unixSocket() error {
	dir, err := os.MkdirTemp("", "go-socket-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(dir)
	return network("unix", filepath.Join(dir, "socket"))
}

func entropy() error {
	var data [64]byte
	if _, err := rand.Read(data[:]); err != nil {
		return err
	}
	if bytes.Equal(data[:32], data[32:]) {
		return fmt.Errorf("identical random blocks")
	}
	return nil
}

func process() error {
	path, err := filepath.Abs(os.Args[0])
	if err != nil {
		return err
	}
	command := exec.Command(path, "child")
	command.Stdin = bytes.NewBufferString("child input")
	command.Env = append(os.Environ(), "GO_QUALIFY_CHILD=present")
	got, err := command.CombinedOutput()
	if err != nil {
		return fmt.Errorf("child: %v: %s", err, got)
	}
	want := fmt.Sprintf("%x present\n", sha256.Sum256([]byte("child input")))
	if string(got) != want {
		return fmt.Errorf("child output %q, want %q", got, want)
	}
	return nil
}

func main() {
	if len(os.Args) == 2 && os.Args[1] == "child" {
		data, err := io.ReadAll(os.Stdin)
		if err != nil {
			os.Exit(1)
		}
		fmt.Printf("%x %s\n", sha256.Sum256(data), os.Getenv("GO_QUALIFY_CHILD"))
		return
	}
	runtime.GOMAXPROCS(2)
	fmt.Printf("GO-QUALIFY: start %s/%s %s\n", runtime.GOOS, runtime.GOARCH, runtime.Version())
	cases := []struct {
		name string
		run  func() error
	}{
		{"scheduler", scheduler},
		{"files", files},
		{"pipe", pipe},
		{"timer", timer},
		{"unix", unixSocket},
		{"tcp", func() error { return network("tcp4", "127.0.0.1:0") }},
		{"entropy", entropy},
		{"process", process},
	}
	selected := "all"
	if len(os.Args) == 2 {
		selected = os.Args[1]
	}
	count := 0
	for _, check := range cases {
		if selected != "all" && selected != check.name {
			continue
		}
		count++
		fmt.Printf("GO-QUALIFY: RUN %s\n", check.name)
		if err := check.run(); err != nil {
			fmt.Printf("GO-QUALIFY: FAIL %s: %v\n", check.name, err)
			os.Exit(1)
		}
		fmt.Printf("GO-QUALIFY: PASS %s\n", check.name)
	}
	if count == 0 {
		fmt.Fprintf(os.Stderr, "unknown check %q\n", selected)
		os.Exit(2)
	}
	fmt.Printf("GO-QUALIFY: PASS %s (%d checks)\n", selected, count)
}
