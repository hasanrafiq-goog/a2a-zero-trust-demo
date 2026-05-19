import asyncio
import os
from calculator_agent.agent import root_agent
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

async def generate():
    # Retrieve the Calculator URL from environment or fallback
    calc_url = os.environ.get("CALCULATOR_URL", "https://calculator-agent-xxx.run.app/")
    
    print(f"🛠 Generating Agent Card for: {calc_url}")
    
    builder = AgentCardBuilder(agent=root_agent, rpc_url=calc_url)
    card = await builder.build()
    
    output_path = "orchestrator_agent/calculator_card.json"
    with open(output_path, "w") as f:
        f.write(card.model_dump_json(indent=2))
    
    print(f"✅ Created local agent card at: {output_path}")

if __name__ == "__main__":
    asyncio.run(generate())
