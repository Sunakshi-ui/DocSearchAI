from pydoc import text
import string
from collections import defaultdict
from typing import Dict, List, Set
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

ps = PorterStemmer()
STOP_WORDS: Set[str] = {"a", "an", "the", "there", "these", "is", "he", "on", "are", "this"}
asymmetric: Set[str] = {"windows"}
processed: List[str] = []

def preprocess(text: str) -> List[str]:
  
  arr = bytearray(256)
  PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)
  text = text.lower().translate(PUNCTUATION_TABLE)

  tokens = text.split()

  for t in tokens:
    if t in STOP_WORDS:
      continue
    if t in asymmetric:
      processed.append(t)

      continue
    processed.append(ps.stem(t))

  for t in processed:
    print(t)
  return processed

