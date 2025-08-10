#!/usr/bin/env python3
"""Knowledge Base Seeding Script for Reflex Executive Assistant."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kb.seeder import KnowledgeBaseSeeder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def seed_all_content():
    """Seed all knowledge base content."""
    seeder = KnowledgeBaseSeeder()
    
    try:
        await seeder.initialize()
        results = await seeder.seed_all()
        
        print("\n" + "="*60)
        print("KNOWLEDGE BASE SEEDING RESULTS")
        print("="*60)
        
        total_documents = 0
        for category, result in results.items():
            if isinstance(result, dict) and "documents_added" in result:
                docs_added = result["documents_added"]
                status = result.get("status", "unknown")
                total_documents += docs_added
                
                print(f"{category.replace('_', ' ').title():<25} | {docs_added:>3} docs | {status}")
        
        print("-"*60)
        print(f"Total Documents Added: {total_documents}")
        print(f"Timestamp: {results.get('timestamp', 'N/A')}")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed knowledge base: {e}")
        return False


async def seed_specific_category(category: str):
    """Seed a specific category of content."""
    seeder = KnowledgeBaseSeeder()
    
    try:
        await seeder.initialize()
        
        # Map category names to methods
        category_methods = {
            "company_info": seeder.seed_company_info,
            "policies": seeder.seed_policies,
            "style_guide": seeder.seed_style_guide,
            "procedures": seeder.seed_procedures,
            "faqs": seeder.seed_faqs,
            "templates": seeder.seed_templates,
            "market_context": seeder.seed_market_context,
            "excluded_markets": seeder.seed_excluded_markets,
            "approval_workflows": seeder.seed_approval_workflows,
            "integration_guides": seeder.seed_integration_guides
        }
        
        if category not in category_methods:
            print(f"Error: Unknown category '{category}'")
            print(f"Available categories: {', '.join(category_methods.keys())}")
            return False
        
        method = category_methods[category]
        result = await method()
        
        print(f"\nSeeding {category.replace('_', ' ')}...")
        print(f"Documents added: {result.get('documents_added', 0)}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        return result.get("status") == "completed"
        
    except Exception as e:
        logger.error(f"Failed to seed category '{category}': {e}")
        return False


async def seed_from_file(file_path: str):
    """Seed knowledge base from a JSON file."""
    seeder = KnowledgeBaseSeeder()
    
    try:
        await seeder.initialize()
        result = await seeder.seed_from_file(Path(file_path))
        
        print(f"\nSeeding from file: {file_path}")
        print(f"Documents added: {result.get('documents_added', 0)}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get("status") == "file_not_found":
            print(f"Error: File '{file_path}' not found")
            return False
        
        return result.get("status") == "completed"
        
    except Exception as e:
        logger.error(f"Failed to seed from file '{file_path}': {e}")
        return False


async def clear_knowledge_base():
    """Clear all documents from the knowledge base."""
    seeder = KnowledgeBaseSeeder()
    
    try:
        await seeder.initialize()
        
        # Confirm with user
        response = input("Are you sure you want to clear the knowledge base? (yes/no): ")
        if response.lower() != "yes":
            print("Operation cancelled.")
            return True
        
        result = await seeder.clear_knowledge_base()
        
        print(f"\nKnowledge base clear result:")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Message: {result.get('message', 'N/A')}")
        
        return result.get("status") == "completed"
        
    except Exception as e:
        logger.error(f"Failed to clear knowledge base: {e}")
        return False


async def get_status():
    """Get the current status of the knowledge base."""
    seeder = KnowledgeBaseSeeder()
    
    try:
        await seeder.initialize()
        status = await seeder.get_seeding_status()
        
        print(f"\nKnowledge Base Status:")
        print(f"Status: {status.get('status', 'unknown')}")
        print(f"Message: {status.get('message', 'N/A')}")
        print(f"Timestamp: {status.get('timestamp', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return False


async def list_categories():
    """List available seeding categories."""
    categories = [
        "company_info",
        "policies", 
        "style_guide",
        "procedures",
        "faqs",
        "templates",
        "market_context",
        "excluded_markets",
        "approval_workflows",
        "integration_guides"
    ]
    
    print("\nAvailable seeding categories:")
    print("-" * 40)
    for i, category in enumerate(categories, 1):
        print(f"{i:2d}. {category.replace('_', ' ').title()}")
    
    print("\nUse 'seed-all' to seed all categories at once.")
    return True


async def create_sample_file():
    """Create a sample JSON file for custom seeding."""
    sample_data = {
        "documents": [
            {
                "content": "This is a sample document for the knowledge base.",
                "metadata": {
                    "type": "sample",
                    "category": "custom",
                    "priority": "medium",
                    "source": "custom_file"
                }
            },
            {
                "content": "Another sample document with different metadata.",
                "metadata": {
                    "type": "example",
                    "category": "custom",
                    "priority": "low",
                    "source": "custom_file"
                }
            }
        ]
    }
    
    sample_file = Path("sample_kb_data.json")
    
    try:
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSample file created: {sample_file}")
        print("You can edit this file and use 'seed-from-file' to load it.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create sample file: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Knowledge Base Seeder for Reflex Executive Assistant")
    parser.add_argument("command", choices=[
        "seed-all", "seed-category", "seed-from-file", "clear", "status", 
        "list-categories", "create-sample"
    ], help="Seeding command to execute")
    
    parser.add_argument("--category", help="Category to seed (for seed-category command)")
    parser.add_argument("--file", help="JSON file to seed from (for seed-from-file command)")
    
    args = parser.parse_args()
    
    # Execute command
    success = False
    
    if args.command == "seed-all":
        success = asyncio.run(seed_all_content())
    elif args.command == "seed-category":
        if not args.category:
            print("Error: Category is required for seed-category command")
            print("Use 'list-categories' to see available categories")
            return 1
        success = asyncio.run(seed_specific_category(args.category))
    elif args.command == "seed-from-file":
        if not args.file:
            print("Error: File path is required for seed-from-file command")
            return 1
        success = asyncio.run(seed_from_file(args.file))
    elif args.command == "clear":
        success = asyncio.run(clear_knowledge_base())
    elif args.command == "status":
        success = asyncio.run(get_status())
    elif args.command == "list-categories":
        success = asyncio.run(list_categories())
    elif args.command == "create-sample":
        success = asyncio.run(create_sample_file())
    
    if success:
        print("\nCommand completed successfully!")
        return 0
    else:
        print("\nCommand failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 