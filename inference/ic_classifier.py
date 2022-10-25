import csv
import hashlib
import os.path
import pathlib

import openai

CACHE_FILE = pathlib.Path(os.path.dirname(__file__), "..", "cache", "utterance_ic.csv")


class UtteranceClassification:
    def __init__(self, utterance_hash: str, is_ic: bool, logprob: float, reason: str):
        self.hash = utterance_hash
        self.is_ic = is_ic
        self.logprob = logprob
        self.reason = reason

    @classmethod
    def from_dict(cls, d):
        return cls(d["hash"], d["classification"], d["logprob"], d["reason"])

    def dict(self):
        return {"hash": self.hash, "classification": self.is_ic, "logprob": self.logprob, "reason": self.reason}


class UtteranceClassifier:
    def __init__(self):
        self.classification_cache: dict[str, UtteranceClassification] = {}

    # ==== methods ====
    @staticmethod
    def _hash_utterance(utterance: str) -> str:
        """Returns the hexdigest of the SHA-256 hash of the normalized utterance."""
        # normalize: trim spaces
        norm = utterance.strip()
        return hashlib.sha256(norm.encode()).hexdigest()

    def _find_cache(self, utterance_digest: str) -> UtteranceClassification | None:
        """If the utterance has been classified before and is cached, return the cached classification."""
        if len(self.classification_cache) == 0:
            self._load_cache()
        return self.classification_cache.get(utterance_digest)

    def _load_cache(self):
        with open(CACHE_FILE, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.classification_cache[row["hash"]] = UtteranceClassification.from_dict(row)

    def _make_openai_inference(self, utterance: str) -> UtteranceClassification:
        response = openai.Completion.create(
            model="code-davinci-002",
            prompt="'\"Hello world!\"'\nin_character: bool = ",
            temperature=0,
            max_tokens=1,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            logprobs=2,
        )

        # {
        #   "id": "cmpl-uqkvlQyYK7bGYrRHQ0eXlWi7",
        #   "object": "text_completion",
        #   "created": 1589478378,
        #   "model": "code-davinci-002",
        #   "choices": [
        #     {
        #       "text": "\n\nThis is a test",
        #       "index": 0,
        #       "logprobs": null,
        #       "finish_reason": "length"
        #     }
        #   ],
        #   "usage": {
        #     "prompt_tokens": 5,
        #     "completion_tokens": 6,
        #     "total_tokens": 11
        #   }
        # }

    def _do_classify(self, utterance: str, digest: str) -> UtteranceClassification:
        cached = self._find_cache(digest)
        if cached is not None:
            return cached

        # any utterance of len 1-2 is classified as OOC
        if len(utterance.split()) < 3:
            return UtteranceClassification(digest, False, 0, "too_short")

        return self._make_openai_inference(utterance)

    def save_cache(self):
        with open(CACHE_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=("hash", "classification", "logprob", "reason"))
            writer.writeheader()
            for elem in self.classification_cache.values():
                writer.writerow(elem.dict())

    def classify_utterance(self, utterance: str) -> UtteranceClassification:
        digest = self._hash_utterance(utterance)
        classification = self._do_classify(utterance, digest)
        self.classification_cache.setdefault(digest, classification)
        return classification
