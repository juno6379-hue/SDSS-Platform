"""Pin final Toolbox source after hover fix; preserve earlier observation evidence."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
read = lambda name: json.loads((root/name).read_text(encoding='utf-8-sig'))
sha = lambda name: hashlib.sha256((root/name).read_bytes()).hexdigest()
before = read('evidence/integration/toolbox-ui-preflight-20261018.json')
sources = ['App.tsx','PlatformShell.tsx','GeoAIToolbox.tsx','geoai-toolbox.css','toolboxAdapter.ts','toolboxAdapter.test.mjs']
details = ['ModelAnalysisWorkspace.tsx','model-workspace.css','LclucWorkflowPanel.tsx','SDSSChrome.tsx','sdss-chrome.css']
hashes = {'frontend/src/'+name:sha('frontend/src/'+name) for name in sources+details}
unchanged = {name:hashes['frontend/src/'+name] == before['frontend/src/'+name]['sha256'] for name in details}
assert all(unchanged.values())
assert hashes['frontend/src/geoai-toolbox.css'] == 'b962623c6e30844547f5c8942b266cac003180f52415c7ea64dcc8220d2393da'
report = {'at_utc':datetime.now(timezone.utc).isoformat(),
    'base':'8cf7b9421ea3d5916058a9e4622dc19c9075e9f2', 'source_sha256':hashes,
    'existing_detail_sources_unchanged':unchanged,
    'frontend':{'pass':293,'fail':0,'skip':0,'milliseconds':52585.8786,'exit':0,
        'scope':'Current main data UI plus Toolbox code. Final subsequent change is CSS-only hover override, checked in live browser and final build.'},
    'final_build':{'exit':0,'modules':123,'vite_seconds':32.54,'css_kb':228.17,'js_kb':1739.26,'warning':'Existing chunk-size warning'},
    'hover':{'before':{'background':[18,110,134],'text':[6,25,119],'heading':[35,76,105]},
        'after':{'background':'linear-gradient(145deg, rgb(255,255,255)65%,rgb(237,246,255))','text':[6,25,119],'heading':[6,25,119]},
        'cause':'Later global button:hover:not(:disabled) rule overrode card background. Scoped Toolbox rules now win and preserve preview imagery/primary buttons.'},
    'browser':{'url':'http://127.0.0.1:5174/#/view/12','actual_hover_observed':True,'hmr_applied':True,
        'lcluc_navigation':'#/view/24?model=lcluc&tab=input','lcluc_heading_count':1,
        'return_to_hub':True,'horizontal_overflow':False,'console_error_warning_count':0},
    'earlier_browser_evidence':'toolbox-ui-final-20261018.json includes six-model navigation and390x844 viewport check; not rerun as if new observations.',
    'latest_readonly_scope_review':'toolbox-ui-current-base-review-20261018.json; its CSS pin predates final hover fix.',
    'evidence':['toolbox-ui-current-frontend-20261018.log','toolbox-ui-hover-build-20261018.log',
        'toolbox-ui-hover-before-20261018.jpg','toolbox-ui-hover-after-20261018.jpg',
        'toolbox-ui-current-browser-20261018.txt','toolbox-ui-current-browser-20261018.jpg'],
    'collector_or_training_changes':0,'server_restarts':0,'api_writes':0,
    'scope_note':'Dataset registry records and collected patch counts are different units; code implementation is not scientific/operational approval.'}
with (root/'evidence/integration/toolbox-ui-current-final-20261018.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print('Final Toolbox source and5 preserved detail hashes recorded.')
