"""Render measured experiment JSON to Markdown, without editing paper sources."""
import argparse
import json
from pathlib import Path


def render(report):
    if report.get('status') != 'MEASURED':
        raise ValueError('Only executed MEASURED results may produce numeric tables')
    lines = ['# Measured experiment results','']
    if 'categories' in report:
        lines += ['| Category | n | Calls | Addresses | Depth | Gas |','|---|---:|---:|---:|---:|---:|']
        for name,row in sorted(report['categories'].items()):
            lines.append(f"| {name} | {row['n']} | {row['function_calls']:.3f} | {row['addresses']:.3f} | {row['max_depth']:.3f} | {row['gas_used']:.3f} |")
    comparisons = report.get('comparisons') or {'paired':report.get('comparison',{})}
    for name,comparison in comparisons.items():
        if not comparison:
            continue
        lines += ['',f'## {name}', '', '| Quantity | Observed value |','|---|---|']
        for key in ('n','accuracy_difference_pp','f1_difference_pp','baseline_cost_usd',
                    'candidate_cost_usd','cost_savings_fraction','latency_savings_fraction','top1_agreement_fraction'):
            value = comparison.get(key)
            lines.append(f'| {key} | {value if value is not None else "Undefined: missing denominator"} |')
        lines += ['', 'Function localization: `'+json.dumps(comparison.get('localization'))+'`.']
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    text = render(json.loads(args.input.read_text(encoding='utf-8-sig')))
    if 'paper' in {part.lower() for part in args.output.parts}:
        raise ValueError('Paper source directories are excluded from generated results')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding='utf-8')


if __name__ == '__main__':
    main()
