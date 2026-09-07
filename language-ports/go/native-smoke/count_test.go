package main

import (
	"reflect"
	"strings"
	"testing"
)

func TestCountsAndOrdering(t *testing.T) {
	got, err := countWords(strings.NewReader("RED blue red green blue red"))
	want := []wordCount{{"red", 3}, {"blue", 2}, {"green", 1}}
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("countWords = %v, %v; want %v", got, err, want)
	}
}

func TestTieAndEmpty(t *testing.T) {
	got, err := countWords(strings.NewReader("b a"))
	if err != nil || len(got) != 2 || got[0].word != "a" {
		t.Fatalf("tie ordering: %v, %v", got, err)
	}
	got, err = countWords(strings.NewReader(""))
	if err != nil || len(got) != 0 {
		t.Fatalf("empty input: %v, %v", got, err)
	}
}
