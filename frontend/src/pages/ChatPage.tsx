import React, { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Brain,
  FileCode,
  Bot,
  User,
  Trash2,
  Copy,
  Check,
  Loader2,
  Send,
} from 'lucide-react';
import Markdown from 'markdown-to-jsx';
import { apiService } from '../services/apiService';
import type { ChatMessage } from '../types';

export const ChatPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();
  const [inputQuery, setInputQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'assistant',
      text: `Hello! I am your **CodeIntel AI Codebase Assistant**.\n\nI index all Python AST structures, NetworkX module graphs, and vector chunks for this repository. Ask me anything about class structures, risk scores, or bug locations!`,
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (queryText: string) =>
      apiService.sendChatMessage({
        repository_id: id,
        query: queryText,
        conversation_history: messages,
      }),
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        text: data.answer,
        sources: data.sources,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    },
    onError: (error: Error) => {
      const errorMessage: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        sender: 'assistant',
        text: `⚠️ **API Error**: ${error.message || 'Failed to query codebase.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    },
  });

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputQuery.trim() || chatMutation.isPending) return;

    const userQuery = inputQuery.trim();
    setInputQuery('');

    const userMessage: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      sender: 'user',
      text: userQuery,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    chatMutation.mutate(userQuery);
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handlePromptSuggestion = (promptText: string) => {
    setInputQuery(promptText);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between glass-panel p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/20">
            <Brain className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <span>AI Codebase Chat Assistant</span>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 rounded-full">
                RAG + AST Graph
              </span>
            </h1>
            <p className="text-xs text-slate-400">Contextual answers grounded by NetworkX module dependencies & vector search</p>
          </div>
        </div>

        <button
          onClick={() => setMessages([messages[0]])}
          className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 text-xs flex items-center space-x-1.5 transition-colors"
          title="Clear Conversation"
        >
          <Trash2 className="h-4 w-4" />
          <span className="hidden sm:inline">Clear Chat</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 glass-panel rounded-2xl border border-slate-800 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
          >
            {/* Avatar */}
            <div
              className={`p-2 rounded-xl flex-shrink-0 ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gradient-to-tr from-cyan-950 to-slate-900 text-cyan-400 border border-cyan-800'
              }`}
            >
              {msg.sender === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            {/* Content Bubble */}
            <div className={`max-w-3xl space-y-3 ${msg.sender === 'user' ? 'text-right' : ''}`}>
              <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                <span>{msg.sender === 'user' ? 'You' : 'CodeIntel AI'}</span>
                <span>•</span>
                <span>{msg.timestamp}</span>
              </div>

              <div
                className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed text-slate-200 ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600/90 text-white rounded-tr-none shadow-md'
                    : 'bg-slate-900/90 border border-slate-800 rounded-tl-none font-sans'
                }`}
              >
                <div className="prose prose-invert prose-xs max-w-none">
                  <Markdown
                    options={{
                      overrides: {
                        pre: {
                          component: ({ children }) => (
                            <div className="relative my-3 rounded-xl bg-slate-950 p-3 border border-slate-800 font-mono text-xs overflow-x-auto">
                              {children}
                            </div>
                          ),
                        },
                        code: {
                          component: ({ children }) => (
                            <code className="bg-slate-950 text-cyan-300 px-1.5 py-0.5 rounded border border-slate-800 font-mono text-xs">
                              {children}
                            </code>
                          ),
                        },
                      },
                    }}
                  >
                    {msg.text}
                  </Markdown>
                </div>
              </div>

              {/* Source Citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2 text-left">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
                    <FileCode className="h-3.5 w-3.5" />
                    <span>Retrieved Code Sources ({msg.sources.length})</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {msg.sources.map((src, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-xs font-mono transition-all flex items-center justify-between"
                      >
                        <div className="truncate">
                          <span className="text-cyan-300 font-semibold">{src.file_path}</span>
                          {src.line_start && (
                            <span className="text-slate-500 ml-1">
                              #L{src.line_start}-{src.line_end}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleCopy(src.file_path, `${msg.id}-${idx}`)}
                          className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
                          title="Copy file path"
                        >
                          {copiedId === `${msg.id}-${idx}` ? (
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {chatMutation.isPending && (
          <div className="flex items-center space-x-3 text-xs text-cyan-400 font-mono animate-pulse">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Analyzing repository AST graph & retrieving context...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Pills */}
      <div className="flex items-center space-x-2 overflow-x-auto py-1 scrollbar-none">
        <span className="text-[11px] font-semibold text-slate-500 uppercase whitespace-nowrap">Suggested:</span>
        <button
          onClick={() => handlePromptSuggestion('Explain the architecture of rag/pipeline.py and its risk score')}
          className="px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 whitespace-nowrap transition-colors"
        >
          💡 Explain rag/pipeline.py architecture
        </button>
        <button
          onClick={() => handlePromptSuggestion('Which files have high memory consumption or bug risks?')}
          className="px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 whitespace-nowrap transition-colors"
        >
          ⚠️ High risk files list
        </button>
        <button
          onClick={() => handlePromptSuggestion('How are duplicate GitHub issues detected by ML?')}
          className="px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 whitespace-nowrap transition-colors"
        >
          🔍 ML Issue duplicate detection
        </button>
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="relative">
        <div className="flex items-center p-2 rounded-2xl glass-panel border border-slate-800 focus-within:border-cyan-500/80 transition-all">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask anything about functions, dependency DAGs, issues, or risk factors..."
            className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none px-3 py-1.5"
          />

          <button
            type="submit"
            disabled={!inputQuery.trim() || chatMutation.isPending}
            className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold text-xs flex items-center space-x-1.5 transition-all disabled:opacity-40 cursor-pointer"
          >
            {chatMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin text-slate-950" />
            ) : (
              <>
                <span>Send</span>
                <Send className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
