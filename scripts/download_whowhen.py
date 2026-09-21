"""Download Who&When Pro text split + taxonomy (Jev is text-only; skip image/video assets)."""
from huggingface_hub import hf_hub_download

tax = hf_hub_download("Leoxx/whowhen_pro", filename="taxonomy.yaml", repo_type="dataset", local_dir="data/whowhen_pro")
print("taxonomy:", tax)
text = hf_hub_download("Leoxx/whowhen_pro", filename="data/text.jsonl", repo_type="dataset", local_dir="data/whowhen_pro")
print("text:", text)
