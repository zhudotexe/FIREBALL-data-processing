export const enum SortOrder {
    NONE = 0,
    ASC = 1,
    DESC = 2
}

// ===== WHATWG Streams Standard =====
// stream manipulation utilities adapted from https://github.com/whatwg/streams
// see "WHATWG Streams Standard" in licenses.txt
export function splitStreamOn(splitOn: string): TransformStream<string, string> {
    let buffer = '';

    return new TransformStream<string, string>({
        transform(chunk, controller) {
            buffer += chunk;
            const parts = buffer.split(splitOn);
            parts.slice(0, -1).forEach(part => controller.enqueue(part));
            buffer = parts[parts.length - 1];
        },
        flush(controller) {
            if (buffer) controller.enqueue(buffer);
        }
    });
}

export function parseJSONStream<T>(): TransformStream<string, T> {
    return new TransformStream<string, T>({
        transform(chunk, controller) {
            controller.enqueue(JSON.parse(chunk));
        }
    });
}

// ===== end WHATWG Streams Standard =====
