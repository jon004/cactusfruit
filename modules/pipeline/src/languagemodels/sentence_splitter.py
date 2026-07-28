import spacy

_NLP = None

def _get_nlp():
    global _NLP

    if _NLP is None:
        _NLP = spacy.load(
            "en_core_web_sm",
            disable=["tagger", "parser", "lemmatizer", "ner"]
        )
        # Add the rule-based sentencizer to handle sentence segmentation
        _NLP.add_pipe("sentencizer")

    return _NLP

def split_sentences(
    text: str,
    min_length: int = 5,
) -> list[str]:
    if not text:
        return []

    text = " ".join(text.split())

    doc = _get_nlp()(text)

    return [
        sent.text.strip()
        for sent in doc.sents
        if len(sent.text.strip()) >= min_length
    ]
