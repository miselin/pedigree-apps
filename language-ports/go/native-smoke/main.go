package main

import (
	"fmt"
	"os"
)

func main() {
	counts, err := countWords(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, entry := range counts {
		fmt.Printf("%s %d\n", entry.word, entry.count)
	}
}
