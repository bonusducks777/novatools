import React from "react"
import Link from "next/link"
import { Search, FileText, BotIcon as Robot, FileCode, Database, MessageSquare } from "lucide-react"

export default function Home() {
  const tools = [
    {
      name: "Crypto Research",
      description: "General crypto info and research with real-time data and charts.",
      icon: Search,
      href: "/research",
    },
    {
      name: "NovaDocs Agentic AI",
      description: "Sort and query through gigantic amounts of paperwork using our Agentic AI",
      icon: FileText,
      href: "/document-qa",
    },
    {
      name: "NovaChat Blockchain AI",
      description: "Natural-Language blockchain bot allowing for casual, easy blockchain interaction",
      icon: Robot,
      href: "/trading-bot",
    },
    {
      name: "AI-assisted Deployer+",
      description: "Easily deploy pre-set contracts including tokens, multisig wallets, and DAOs.",
      icon: FileCode,
      href: "/contract-deployer",
    }
  ]

  return (
    <div className="flex items-center justify-center min-h-[calc(80vh-4rem)]">
      <div className="max-w-4xl mx-auto space-y-5">
        <h1 className="text-4xl font-bold text-primary title-underline">Welcome to Crypto-AI Suite</h1>
        <p className="text-lg text-muted-foreground">
          Explore our set of AI-powered tools for cryptocurrency research, analysis, and management. Click
          on a tool below or select from the sidebar to get started.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tools.map((tool, index) => (
            <Link key={index} href={tool.href} className="block">
              <div className="bg-card text-card-foreground p-6 rounded-lg border border-border hover:border-accent transition-colors">
                <div className="flex items-center space-x-3 mb-2">
                  {React.createElement(tool.icon, { className: "w-6 h-6 text-primary" })}
                  <h2 className="text-xl font-semibold title-underline">{tool.name}</h2>
                </div>
                <p className="text-muted-foreground">{tool.description}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

