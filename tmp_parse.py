import json
j=json.load(open('benchmark/eval_results/eval_20260404_234634.json'))
m=j['metrics'].get('signal_metrics',{})

print('METRICS---------------------')
for k,v in m.items():
    if v['support']>0:
        print(f"{k:35} TP:{v['TP']} FP:{v['FP']} FN:{v['FN']} (n={v['support']})")

print('\nFAILURES--------------------')
for f in j['metrics'].get('failures',[]):
    print(f.get('tx')[:10], f.get('signal'))
