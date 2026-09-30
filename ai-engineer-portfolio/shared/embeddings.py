from __future__ import annotations
import hashlib, math, re
from functools import lru_cache
import httpx
from .core import settings
DIMENSIONS=384

def _features(text:str)->list[float]:
    """Deterministic signed feature hashing; offline baseline, not a pretrained semantic model."""
    vector=[0.0]*DIMENSIONS
    tokens=re.findall(r"[\w]+",text.casefold(),flags=re.UNICODE)
    features=list(tokens)
    for token in tokens:
        padded=f"^{token}$"
        features.extend(padded[i:i+3] for i in range(max(0,len(padded)-2)))
    for feature in features:
        digest=hashlib.blake2b(feature.encode("utf-8"),digest_size=8).digest()
        index=int.from_bytes(digest[:4],"little")%DIMENSIONS
        sign=1.0 if digest[4]&1 else -1.0
        vector[index]+=sign
    norm=math.sqrt(sum(x*x for x in vector))
    return [x/norm for x in vector] if norm else vector

@lru_cache(maxsize=1)
def _local_semantic_model(model_name:str):
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise RuntimeError("Local semantic embeddings require `pip install -e '.[semantic]'`.") from exc
    return TextEmbedding(model_name=model_name,threads=2)

def embed_texts(texts:list[str],*,input_type:str="passage")->list[list[float]]:
    if input_type not in {"query","passage"}:
        raise ValueError("input_type must be query or passage")
    if settings.embedding_mode=="hash": return [_features(text) for text in texts]
    if settings.embedding_mode=="fastembed":
        model=_local_semantic_model(settings.fastembed_model)
        method=model.query_embed if input_type=="query" else model.passage_embed
        return [[float(value) for value in vector] for vector in method(texts)]
    if not settings.openai_api_key: raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_MODE=openai")
    result=[]
    for start in range(0,len(texts),64):
        batch=texts[start:start+64]
        response=httpx.post("https://api.openai.com/v1/embeddings",headers={"Authorization":f"Bearer {settings.openai_api_key}"},json={"model":settings.embedding_model,"input":batch,"dimensions":DIMENSIONS},timeout=httpx.Timeout(45,connect=5))
        response.raise_for_status()
        result.extend(item["embedding"] for item in sorted(response.json()["data"],key=lambda item:item["index"]))
    return result

def cosine_similarity(left:list[float],right:list[float])->float:
    if not left or len(left)!=len(right): return 0.0
    denom=math.sqrt(sum(v*v for v in left))*math.sqrt(sum(v*v for v in right))
    return sum(a*b for a,b in zip(left,right))/denom if denom else 0.0
