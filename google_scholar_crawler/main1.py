from scholarly import scholarly, ProxyGenerator
import jsonpickle
import json
from datetime import datetime
import os

proxy_url = "http://localhost:7897"

def set_proxy(url=proxy_url):
    if url:
        os.environ["http_proxy"] = url
        os.environ["https_proxy"] = url
        os.environ["HTTP_PROXY"] = url
        os.environ["HTTPS_PROXY"] = url

set_proxy(proxy_url)
# Setup proxy
# pg = ProxyGenerator()
# pg.FreeProxies()  # Use free rotating proxies
# scholarly.use_proxy(pg)

os.environ['GOOGLE_SCHOLAR_ID'] = "hQpTPuEAAAAJ&hl"
os.makedirs('results', exist_ok=True)
author: dict = scholarly.search_author_id(os.environ['GOOGLE_SCHOLAR_ID'])
scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
name = author['name']
author['updated'] = str(datetime.now())
author['publications'] = {v['author_pub_id']:v for v in author['publications']}
# print(json.dumps(author, indent=2))
with open(f'results/gs_data.json', 'w', encoding="utf-8") as outfile:
    json.dump(author, outfile, ensure_ascii=False)

shieldio_data = {
  "schemaVersion": 1,
  "label": "citations",
  "message": f"{author['citedby']}",
}
with open(f'results/gs_data_shieldsio.json', 'w', encoding='utf-8') as outfile:
    json.dump(shieldio_data, outfile, ensure_ascii=False)




