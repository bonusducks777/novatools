# NovaTools
A suite of crypto-ai tools to make all crypto easy.


## Pitch & Demo

Complete pitch and demo:
http://www.youtube.com/watch?v=1Y02RWJsVo4

Demo begins at 4:01 (https://youtu.be/1Y02RWJsVo4?t=240)


## Features

- Light/dark mode toggle
- NovaBot - Local NLP-blockchain interface bot which works across BNB-chain and AVAX C-chain currently. Tested on mainnet with PancakeSwap and LFJ respectively.
- NovaDocs - Agentic AI Crypto-Specialized Document analyser - local specialised agents digest data from uploaded pdfs and are co-ordinated by a senior agent to output a summary. Data can be surfed, summarized or evaluated in a crypto-context. Great for giant pieces of documentation or whitepapers.
- Light/dark mode toggle
- Features a light/dark mode toggle if you didn't notice





## Installation

Setup Ollama for llama3.2 for port 11434:
```bash
ollama serve
```

UI framework setup for port 3000(UI project root):

```bash
  npm install
  npm run build
  npm run dev
```

NovaDocs setup for port 7860 (project root):
```bash
python contextualtickboxes.py
```

NovaBot setup for port 5000 (project root):
```bash
python web_ui.py
```
    
