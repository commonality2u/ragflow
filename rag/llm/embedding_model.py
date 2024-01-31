#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from abc import ABC

import dashscope
from openai import OpenAI
from FlagEmbedding import FlagModel
import torch
import os
import numpy as np

from rag.utils import num_tokens_from_string

flag_model = FlagModel("BAAI/bge-large-zh-v1.5",
                       query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：",
                       use_fp16=torch.cuda.is_available())

class Base(ABC):
    def __init__(self, key, model_name):
        pass


    def encode(self, texts: list, batch_size=32):
        raise NotImplementedError("Please implement encode method!")

    def encode_queries(self, text: str):
        raise NotImplementedError("Please implement encode method!")


class HuEmbedding(Base):
    def __init__(self, key="", model_name=""):
        """
        If you have trouble downloading HuggingFace models, -_^ this might help!!

        For Linux:
        export HF_ENDPOINT=https://hf-mirror.com

        For Windows:
        Good luck
        ^_-

        """
        self.model = flag_model


    def encode(self, texts: list, batch_size=32):
        token_count = 0
        for t in texts: token_count += num_tokens_from_string(t)
        res = []
        for i in range(0, len(texts), batch_size):
            res.extend(self.model.encode(texts[i:i + batch_size]).tolist())
        return np.array(res), token_count

    def encode_queries(self, text: str):
        token_count = num_tokens_from_string(text)
        return self.model.encode_queries([text]).tolist()[0], token_count


class OpenAIEmbed(Base):
    def __init__(self, key, model_name="text-embedding-ada-002"):
        self.client = OpenAI(api_key=key)
        self.model_name = model_name

    def encode(self, texts: list, batch_size=32):
        res = self.client.embeddings.create(input=texts,
                                            model=self.model_name)
        return np.array([d.embedding for d in res.data]), res.usage.total_tokens

    def encode_queries(self, text):
        res = self.client.embeddings.create(input=[text],
                                            model=self.model_name)
        return np.array(res.data[0].embedding), res.usage.total_tokens


class QWenEmbed(Base):
    def __init__(self, key, model_name="text_embedding_v2"):
        dashscope.api_key = key
        self.model_name = model_name

    def encode(self, texts: list, batch_size=10):
        import dashscope
        res = []
        token_count = 0
        texts = [txt[:2048] for txt in texts]
        for i in range(0, len(texts), batch_size):
            resp = dashscope.TextEmbedding.call(
                model=self.model_name,
                input=texts[i:i+batch_size],
                text_type="document"
            )
            embds = [[]] * len(resp["output"]["embeddings"])
            for e in resp["output"]["embeddings"]:
                embds[e["text_index"]] = e["embedding"]
            res.extend(embds)
            token_count += resp["usage"]["input_tokens"]
        return np.array(res), token_count

    def encode_queries(self, text):
        resp = dashscope.TextEmbedding.call(
                model=self.model_name,
                input=text[:2048],
                text_type="query"
            )
        return np.array(resp["output"]["embeddings"][0]["embedding"]), resp["usage"]["input_tokens"]