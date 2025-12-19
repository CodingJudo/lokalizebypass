"""CLI entrypoint."""

import argparse
import sys
from pathlib import Path

from src.memory import build_memory
from src.validate.schema import validate_llm_output, validate_translation_entry
from src.merge import merge_translations
from src.translate import translate_missing
from src.report import generate_summary_report, print_summary_report
from src.providers.ollama import OllamaProvider
from src.providers.api import APIProvider
from src.providers.openai import OpenAIProvider
from src.run_logging import RunLogger


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="i18n LLM Translator - Build memory artifact"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # build-memory command
    build_parser = subparsers.add_parser(
        "build-memory",
        help="Generate work/memory.jsonl from i18n/*.json"
    )
    build_parser.add_argument(
        "--i18n-dir",
        type=Path,
        default=Path("i18n"),
        help="Directory containing i18n JSON files (default: i18n)"
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        default=Path("work/memory.jsonl"),
        help="Output memory.jsonl file (default: work/memory.jsonl)"
    )
    build_parser.add_argument(
        "--source-lang",
        default="sv",
        help="Source language code (default: sv)"
    )
    
    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate LLM translation output"
    )
    validate_parser.add_argument(
        "response_file",
        type=Path,
        help="Path to LLM response file (JSON)"
    )
    
    # write-back command
    write_back_parser = subparsers.add_parser(
        "write-back",
        help="Merge translations from memory.jsonl into i18n files"
    )
    write_back_parser.add_argument(
        "--memory-file",
        type=Path,
        default=Path("work/memory.jsonl"),
        help="Path to memory.jsonl file (default: work/memory.jsonl)"
    )
    write_back_parser.add_argument(
        "--i18n-dir",
        type=Path,
        default=Path("i18n"),
        help="Directory containing i18n JSON files (default: i18n)"
    )
    write_back_parser.add_argument(
        "--target-lang",
        required=True,
        help="Target language code to merge into"
    )
    write_back_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty translations"
    )
    
    # translate-missing command
    translate_parser = subparsers.add_parser(
        "translate-missing",
        help="Translate missing keys for a target language"
    )
    translate_parser.add_argument(
        "--memory-file",
        type=Path,
        default=Path("work/memory.jsonl"),
        help="Path to memory.jsonl file (default: work/memory.jsonl)"
    )
    translate_parser.add_argument(
        "--target-lang",
        required=True,
        help="Target language code to translate"
    )
    translate_parser.add_argument(
        "--source-lang",
        default="sv",
        help="Source language code (default: sv)"
    )
    translate_parser.add_argument(
        "--provider",
        choices=["ollama", "api", "openai"],
        default="ollama",
        help="Translation provider (default: ollama)"
    )
    translate_parser.add_argument(
        "--model",
        default="llama3.1:latest",
        help="Ollama model name (default: llama3.1:latest). Ignored if --provider is openai."
    )
    translate_parser.add_argument(
        "--openai-model",
        help="OpenAI model name (default: from OPENAI_MODEL env or gpt-4o-mini). Only used if --provider is openai."
    )
    translate_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for translations (default: 10)"
    )
    translate_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("work/runs"),
        help="Directory for run logs (default: work/runs)"
    )
    translate_parser.add_argument(
        "--context",
        type=str,
        help="Global context for translations (e.g., 'This is a mobile app. Use friendly, casual tone.')"
    )
    translate_parser.add_argument(
        "--context-file",
        type=Path,
        help="Path to file containing global context (alternative to --context)"
    )
    
    # run command (end-to-end)
    run_parser = subparsers.add_parser(
        "run",
        help="End-to-end translation: build-memory -> translate-missing -> write-back"
    )
    run_parser.add_argument(
        "--i18n-dir",
        type=Path,
        default=Path("i18n"),
        help="Directory containing i18n JSON files (default: i18n)"
    )
    run_parser.add_argument(
        "--memory-file",
        type=Path,
        default=Path("work/memory.jsonl"),
        help="Path to memory.jsonl file (default: work/memory.jsonl)"
    )
    run_parser.add_argument(
        "--target-lang",
        required=True,
        help="Target language code to translate"
    )
    run_parser.add_argument(
        "--source-lang",
        default="sv",
        help="Source language code (default: sv)"
    )
    run_parser.add_argument(
        "--provider",
        choices=["ollama", "api", "openai"],
        default="ollama",
        help="Translation provider (default: ollama)"
    )
    run_parser.add_argument(
        "--model",
        default="llama3.1:latest",
        help="Ollama model name (default: llama3.1:latest). Ignored if --provider is openai."
    )
    run_parser.add_argument(
        "--openai-model",
        help="OpenAI model name (default: from OPENAI_MODEL env or gpt-4o-mini). Only used if --provider is openai."
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for translations (default: 10)"
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty translations when writing back"
    )
    run_parser.add_argument(
        "--skip-translate",
        action="store_true",
        help="Skip translation step (useful for testing write-back)"
    )
    run_parser.add_argument(
        "--context",
        type=str,
        help="Global context for translations (e.g., 'This is a mobile app. Use friendly, casual tone.')"
    )
    run_parser.add_argument(
        "--context-file",
        type=Path,
        help="Path to file containing global context (alternative to --context)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "build-memory":
        try:
            build_memory(
                i18n_dir=args.i18n_dir,
                output_file=args.output,
                source_lang=args.source_lang
            )
            print(f"✓ Built memory artifact: {args.output}")
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "validate":
        try:
            with open(args.response_file, "r", encoding="utf-8") as f:
                response_text = f.read()
            
            is_valid, data, error_msg = validate_llm_output(response_text)
            
            if is_valid:
                print(f"✓ Valid LLM output")
                print(f"  Target language: {data['targetLanguage']}")
                print(f"  Translations: {len(data['translations'])}")
            else:
                print(f"✗ Invalid LLM output: {error_msg}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "write-back":
        try:
            stats = merge_translations(
                memory_file=args.memory_file,
                i18n_dir=args.i18n_dir,
                target_lang=args.target_lang,
                force=args.force
            )
            print(f"✓ Merged translations into {args.i18n_dir}/{args.target_lang}.json")
            print(f"  Updated: {stats['updated']}")
            print(f"  Skipped: {stats['skipped']}")
            if stats['errors']:
                for error in stats['errors']:
                    print(f"  Error: {error}", file=sys.stderr)
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "translate-missing":
        try:
            # Load context
            global_context = args.context
            if args.context_file:
                if args.context_file.exists():
                    with open(args.context_file, "r", encoding="utf-8") as f:
                        global_context = f.read().strip()
                else:
                    print(f"Warning: Context file not found: {args.context_file}", file=sys.stderr)
            
            # Initialize provider
            if args.provider == "ollama":
                provider = OllamaProvider(model=args.model)
            elif args.provider == "api":
                provider = APIProvider()
            elif args.provider == "openai":
                model = args.openai_model  # None if not provided, will use env/default
                provider = OpenAIProvider(model=model)
            else:
                raise ValueError(f"Unknown provider: {args.provider}")
            
            # Initialize logger
            logger = RunLogger(args.runs_dir)
            logger.update_summary(target_language=args.target_lang)
            
            # Translate missing keys
            stats = translate_missing(
                memory_file=args.memory_file,
                target_lang=args.target_lang,
                source_lang=args.source_lang,
                provider=provider,
                logger=logger,
                batch_size=args.batch_size,
                global_context=global_context
            )
            
            # Update logger and finalize
            logger.update_summary(
                batches_processed=stats["batches_processed"],
                items_translated=stats["items_translated"],
                validation_errors=stats["validation_errors"]
            )
            logger.finalize()
            
            # Generate and print report
            report = generate_summary_report(
                args.memory_file,
                args.target_lang,
                stats
            )
            print_summary_report(report)
            
            print(f"✓ Translation complete. Run ID: {logger.run_id}")
            print(f"  Logs: {logger.run_dir}")
        
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    elif args.command == "run":
        try:
            # Step 1: Build memory
            print("Step 1: Building memory artifact...")
            build_memory(
                i18n_dir=args.i18n_dir,
                output_file=args.memory_file,
                source_lang=args.source_lang
            )
            print(f"✓ Built memory artifact: {args.memory_file}")
            
            # Step 2: Translate missing (unless skipped)
            if not args.skip_translate:
                print(f"\nStep 2: Translating missing keys for {args.target_lang}...")
                
                # Load context
                global_context = args.context
                if args.context_file:
                    if args.context_file.exists():
                        with open(args.context_file, "r", encoding="utf-8") as f:
                            global_context = f.read().strip()
                    else:
                        print(f"Warning: Context file not found: {args.context_file}", file=sys.stderr)
                
                # Initialize provider
                if args.provider == "ollama":
                    provider = OllamaProvider(model=args.model)
                elif args.provider == "api":
                    provider = APIProvider()
                elif args.provider == "openai":
                    model = args.openai_model  # None if not provided, will use env/default
                    provider = OpenAIProvider(model=model)
                else:
                    raise ValueError(f"Unknown provider: {args.provider}")
                
                # Initialize logger
                logger = RunLogger(Path("work/runs"))
                logger.update_summary(target_language=args.target_lang)
                
                # Translate missing keys
                stats = translate_missing(
                    memory_file=args.memory_file,
                    target_lang=args.target_lang,
                    source_lang=args.source_lang,
                    provider=provider,
                    logger=logger,
                    batch_size=args.batch_size,
                    global_context=global_context
                )
                
                # Update logger and finalize
                logger.update_summary(
                    batches_processed=stats["batches_processed"],
                    items_translated=stats["items_translated"],
                    validation_errors=stats["validation_errors"]
                )
                logger.finalize()
                
                # Generate and print report
                report = generate_summary_report(
                    args.memory_file,
                    args.target_lang,
                    stats
                )
                print_summary_report(report)
                
                print(f"✓ Translation complete. Run ID: {logger.run_id}")
            else:
                print("⏭ Skipping translation step")
                stats = {"items_translated": 0, "validation_errors": 0}
            
            # Step 3: Write back
            print(f"\nStep 3: Writing back translations to {args.i18n_dir}/{args.target_lang}.json...")
            merge_stats = merge_translations(
                memory_file=args.memory_file,
                i18n_dir=args.i18n_dir,
                target_lang=args.target_lang,
                force=args.force
            )
            print(f"✓ Merged translations")
            print(f"  Updated: {merge_stats['updated']}")
            print(f"  Skipped: {merge_stats['skipped']}")
            
            print(f"\n✓ End-to-end run complete!")
        
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

