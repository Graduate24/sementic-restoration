from transformers import AutoModel, AutoTokenizer
import torch

# 指定本地模型路径
model_path = "/home/ran/Documents/work/graduate/llm-agent/models/codebert"

# 加载 tokenizer 和 model
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModel.from_pretrained(model_path)

def encode(texts):
    # 对输入文本进行编码
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    outputs = model(**inputs)
    # 使用最后一层隐藏状态
    embeddings = outputs.last_hidden_state
    attention_mask = inputs["attention_mask"].unsqueeze(-1).expand(embeddings.size()).float()
    # 进行 masked 平均池化
    masked_embeddings = embeddings * attention_mask
    summed = torch.sum(masked_embeddings, dim=1)
    counts = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
    mean_pooled = summed / counts
    return mean_pooled.detach().numpy()

# 测试
texts = ["这是测试文本", "另一个文本"]
embeddings = encode(texts)
print(embeddings.shape)
