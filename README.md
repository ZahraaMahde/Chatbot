#Axion AI Chatbot
AI-powered sales assistant for Axion, integrated with Odoo 19 inventory.

#Architecture
User → FastAPI → Intent Router → Catalog Search (Supabase) → LLM (GPT-4o-mini) → Response
                                  ↑
                          Odoo 19 Webhooks (background sync)
                          
#Features

Product search with live pricing and stock (synced from Odoo via webhooks)
RAG knowledge base from PDF documents
Conversation memory within sessions
Voice input via Whisper transcription
Bilingual (English + Arabic)
