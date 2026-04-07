import glob, json, sys, time
end = time.time() + 180
while time.time() < end:
    files = sorted(glob.glob('benchmark/eval_results/eval_*.json'))
    if files:
        with open(files[-1]) as f:
            j = json.load(f)
        if j['metrics'].get('total', 0) >= 19:
            print(f"DONE: {files[-1]}")
            sys.exit(0)
    time.sleep(10)
print("TIMEOUT")
sys.exit(1)
