"""
Main entry point for Reverse-Engineered Reasoning Code Repair System
"""
import argparse
import json
from core.repair_pipeline import RepairPipeline
from data_loader import RepairDataLoader


def main():
    parser = argparse.ArgumentParser(
        description="Reverse-Engineered Reasoning for Code Repair"
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input file (JSON) or database path'
    )
    parser.add_argument(
        '--input-type',
        type=str,
        choices=['json', 'database', 'single'],
        default='json',
        help='Type of input file'
    )
    parser.add_argument(
        '--codebase-path',
        type=str,
        default='.',
        help='Path to codebase root (for grep operations)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of cases to process'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output JSON file path'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = RepairPipeline(codebase_path=args.codebase_path)
    
    # Load data
    loader = RepairDataLoader()
    
    if args.input_type == 'json':
        cases = loader.load_from_json(args.input)
    elif args.input_type == 'database':
        loader.db_path = args.input
        cases = loader.load_from_database(limit=args.limit)
    else:  # single
        with open(args.input, 'r', encoding='utf-8') as f:
            case_data = json.load(f)
        cases = [loader.load_from_dict(case_data)]
    
    if args.limit:
        cases = cases[:args.limit]
    
    print(f"Loaded {len(cases)} repair cases")
    
    # Process cases
    results = pipeline.batch_process(cases)
    
    # Save results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {args.output}")
    else:
        print("\nResults:")
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

