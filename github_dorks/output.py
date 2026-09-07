"""Streaming result writers for supported output formats."""

import csv
import json
from dataclasses import asdict


FIELDNAMES = ('dork', 'text_matches', 'path', 'score', 'url')
CSV_HEADERS = (
    'Issue Type (Dork)', 'Text Matches', 'File Path',
    'Score/Relevance', 'URL of File',
)


class TextWriter:
    def __init__(self, stream):
        self.stream = stream

    def start(self):
        pass

    def write(self, result):
        self.stream.write('\n'.join([
            'Found result for {dork}',
            'Text matches: {text_matches}',
            'File path: {path}',
            'Score/Relevance: {score}',
            'URL of File: {url}',
            '',
        ]).format(**result) + '\n')

    def finish(self, stats):
        pass


class CsvWriter:
    def __init__(self, stream):
        self.writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)

    def start(self):
        self.writer.writerow(dict(zip(FIELDNAMES, CSV_HEADERS)))

    def write(self, result):
        self.writer.writerow(result)

    def finish(self, stats):
        pass


class JsonWriter:
    def __init__(self, stream):
        self.stream = stream
        self.first_result = True

    def start(self):
        self.stream.write('{"results":[')

    def write(self, result):
        if not self.first_result:
            self.stream.write(',')
        json.dump(result, self.stream, default=str, separators=(',', ':'))
        self.first_result = False

    def finish(self, stats):
        self.stream.write('],"summary":')
        json.dump(asdict(stats), self.stream, separators=(',', ':'))
        self.stream.write('}\n')


class JsonLinesWriter:
    def __init__(self, stream):
        self.stream = stream

    def start(self):
        pass

    def write(self, result):
        json.dump(
            {'type': 'result', **result}, self.stream,
            default=str, separators=(',', ':'),
        )
        self.stream.write('\n')

    def finish(self, stats):
        json.dump(
            {'type': 'summary', **asdict(stats)}, self.stream,
            separators=(',', ':'),
        )
        self.stream.write('\n')


WRITERS = {
    'text': TextWriter,
    'csv': CsvWriter,
    'json': JsonWriter,
    'jsonl': JsonLinesWriter,
}


def create_writer(output_format, stream):
    try:
        return WRITERS[output_format](stream)
    except KeyError as error:
        supported = ', '.join(WRITERS)
        raise ValueError(
            f'unsupported output format {output_format!r}; choose from {supported}'
        ) from error
