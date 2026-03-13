import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Search } from 'lucide-react';

const ChatPanel = ({ messages, onSendMessage, loading }) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !loading) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div className="main-content glass-panel animate-fade-in">
            <div className="chat-history">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full opacity-50">
                        <Search size={48} className="mb-4 text-accent-primary" />
                        <p className="text-lg">Ask a clinical research question to begin...</p>
                        <p className="text-sm">e.g., "Latest guidelines for heart failure in T2DM patients"</p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-full bg-accent-soft flex items-center justify-center text-accent-primary">
                                    <Bot size={18} />
                                </div>
                            )}
                            <div className={`max-w-[80%] p-4 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-accent-secondary text-white rounded-tr-none'
                                    : 'bg-white/5 border border-white/5 rounded-tl-none'
                                }`}>
                                <p className="m-0 text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                            </div>
                            {msg.role === 'user' && (
                                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-text-secondary">
                                    <User size={18} />
                                </div>
                            )}
                        </div>
                    ))
                )}
                {loading && (
                    <div className="flex gap-4 justify-start">
                        <div className="w-8 h-8 rounded-full bg-accent-soft flex items-center justify-center text-accent-primary">
                            <Bot size={18} />
                        </div>
                        <div className="bg-white/5 border border-white/5 p-4 rounded-2xl rounded-tl-none flex items-center gap-3">
                            <Loader2 className="animate-spin text-accent-primary" size={18} />
                            <span className="text-sm text-text-secondary">Synthesising evidence from PubMed...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="input-area border-t border-white/5 bg-black/20">
                <div className="relative">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Search medical literature (e.g., PICO question)..."
                        className="w-full pr-12 resize-none h-14 pt-3"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="absolute right-3 top-3 p-1.5 rounded-lg bg-accent-primary text-secondary hover:opacity-80 transition-opacity disabled:opacity-50"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ChatPanel;
