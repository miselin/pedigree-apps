package main

import (
	"bufio"
	"io"
	"sort"
	"strings"
)

type wordCount struct {
	word  string
	count int
}

func countWords(input io.Reader) ([]wordCount, error) {
	counts := make(map[string]int)
	scanner := bufio.NewScanner(input)
	scanner.Split(bufio.ScanWords)
	for scanner.Scan() {
		counts[strings.ToLower(scanner.Text())]++
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	result := make([]wordCount, 0, len(counts))
	for word, count := range counts {
		result = append(result, wordCount{word, count})
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].count != result[j].count {
			return result[i].count > result[j].count
		}
		return result[i].word < result[j].word
	})
	return result, nil
}
