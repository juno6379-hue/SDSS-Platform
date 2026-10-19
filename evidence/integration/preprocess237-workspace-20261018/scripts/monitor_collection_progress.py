"""현재 수집을 읽기만 하고 의미있는 변화 때 소유 문서만 갱신한다. HTTP 없음."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import argparse
import os
import time

from audit_data_g0_g1 import ROOT, main as capture

NAMES = {"south_sulawesi":"남술라웨시","gorontalo":"고론탈로","southeast_sulawesi":"남동술라웨시",
         "east_java":"동자바","banten":"반텐","west_java":"서자바"}


def replace_owned_sections(text, heading, last_section, replacement):
    """소유한상태절만교체하고뒤에추가된다른작업자의절은그대로보존한다."""
    start = text.index(heading)
    end = len(text)
    for match in re.finditer(r"(?m)^## (\d+)\.",text[start:]):
        if int(match.group(1)) > last_section:
            end = start + match.start()
            break
    return text[:start]+replacement.rstrip()+"\n\n"+text[end:]


def main():
    path = capture()
    evidence = json.loads(path.read_text(encoding="utf-8"))
    c,b = evidence["collection"], evidence["budget"]
    physical,eligible = c["physical_patches"],c["manifest_quality_eligible_patches"]
    marker = f"physical={physical};eligible={eligible};coverage={c['covered_province_year_cells']};rate_limit={b['rate_limit_active']};errors={len(c['source_attempt_errors'])}"
    progress = ROOT / "docs/implementation/progress_data.md"
    if progress.exists() and marker in progress.read_text(encoding="utf-8"):
        print(json.dumps({"documentation_updated":False,"reason":"no material count/coverage/error/rate-limit change"}))
        return evidence
    when = datetime.fromisoformat(evidence["snapshot_started_at"]).astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S KST")
    ref = path.relative_to(ROOT).as_posix()
    matrix = c["eligible_by_province_year"]
    deficits = {p:{y:max(0,28-n) for y,n in years.items()} for p,years in matrix.items()}
    need = sum(sum(years.values()) for years in deficits.values())
    empty = [f"{NAMES[p]}{year}" for p,years in matrix.items() for year,n in years.items() if not n]
    errors = c["source_attempt_errors"]
    error_lines = [f"- {e['aoi']} / {e['year']}: {e['sanitized_message']} (HTTP상태={e['http_status']})." for e in errors]
    section = [f"## 8. 주기 진행상황 — {when} 스냅샷","",
        f"실행session89858/coordinator/원장/수집코드는변경하지않고읽기만했다. 누적 **{physical}개물리패치/{eligible}개품질적격**/{physical-eligible}개비적격,적격coverage **{c['covered_province_year_cells']}/36셀**,split train/val/test={c['split_counts']['train']}/{c['split_counts']['val']}/{c['split_counts']['test']}다. 1000개하한·클래스균형·독립검증은별도이며학습준비완료로표시하지않는다.","",
        "| 주 | 적격 패치 수 (연도별) |","|---|---|"]
    section += [f"| {NAMES[p]} | "+", ".join(f"{year}:{n}" for year,n in years.items())+" |" for p,years in matrix.items()]
    section += ["",f"적격0셀: {', '.join(empty) if empty else '없음'}. 적격0은공급자원본제품부재를뜻하지않는다. evidence=`{ref}`.","",
        f"신규예약/계측차감상한 {b['new_reserved_or_measured_bytes']:,}B(중pending예약 {b['pending_reserved_bytes']:,}B)/신규상한 {b['new_budget_maximum_bytes']:,}B. 과거계상 {b['historical_charged_upper_bound_bytes']:,}B/종합상한 {b['combined_maximum_bytes']:,}B는불변이다. 이숫자는전체실수신바이트가아니다. 원장내부합계일치={b['ledger_internal_sum_matches']},공유429회로={b['rate_limit_active']}.","",
        f"label_source분포={c['label_sources']},label_year/year불일치={c['wrong_label_year_count']}. 동년참조만유지하고WorldCover2021을다른연도라벨로대체하지않는다. 완료소스시도상태={c['source_attempt_statuses']}. 관측실패사유와HTTP429를구분한다.",""]+error_lines+["",
        f"읽기시pending={evidence['running_evidence']['pending_batches']}. lock/pending만으로프로세스건강·완료를확정하지않는다. 추가네트워크/재시도/원장수정없음.","",
        "## 9. 6주×6년 패치 배분 기준","",
        f"셀당28개계획바닥(36×28=1008)에대한현재추가필요량은 **{need}개**,달성시누적 **{eligible+need}개**다. 각각max(0,28-현재적격수)로계산하며품질/균형합격기준은아니다.","",
        "| 주 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 추가 합계 |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    section += [f"| {NAMES[p]} | "+" | ".join(str(n) for n in years.values())+f" | {sum(years.values())} |" for p,years in deficits.items()]
    section += ["| 합계 | "+" | ".join(str(sum(years[str(y)] for years in deficits.values())) for y in range(2020,2026))+f" | {need} |","",
        f"1000~3000적격패치범위를목표로하며무제한수집하지않는다. 현재1000총량까지는{max(0,1000-eligible)}개,3000상한까지는{max(0,3000-eligible)}개다. 부족클래스·기간·분할누출·독립검증조건은별도확인한다.",""]
    doc20 = ROOT / "docs/20_대량수집_학습_통합실행.md"
    text = doc20.read_text(encoding="utf-8")
    doc20.write_text(replace_owned_sections(text,"## 8. 주기 진행상황",9,"\n".join(section)),encoding="utf-8")
    doc16 = ROOT / "docs/16_충분학습자료_단계별수집계획.md"
    text = doc16.read_text(encoding="utf-8")
    summary = f"## 6. 주기 상태 갱신 — {when}\n\n{physical}물리/{eligible}적격/{physical-eligible}비적격,{c['covered_province_year_cells']}/36셀. split train/val/test={c['split_counts']['train']}/{c['split_counts']['val']}/{c['split_counts']['test']}. 신규예약/계측{b['new_reserved_or_measured_bytes']:,}B중pending{b['pending_reserved_bytes']:,}B,신규4GiB/기존원장불변,429회로={b['rate_limit_active']}. 이숫자는전체실수신량이아니다. 원본session89858/collector/원장변경0.\n\n동년Esri참조만사용하며WC2021연도대체금지,year불일치={c['wrong_label_year_count']}. 적격0셀={', '.join(empty)}. 누적실패시도{len(errors)}건은docs20§8에원인별기록한다. 셀당28개바닥까지추가{need}개/총{eligible+need}개이며개수만으로학습승인하지않는다.\n\n고정증거: `{ref}`. 상세행렬/오류/진행중pending은docs20§8-9.\n"
    doc16.write_text(replace_owned_sections(text,"## 6. 주기 상태 갱신",6,summary),encoding="utf-8")
    progress.write_text(f"# 데이터 수집 읽기전용 진행 기록\n\n<!-- {marker} -->\n\n{summary}\n",encoding="utf-8")
    print(json.dumps({"documentation_updated":True,"physical":physical,"eligible":eligible,"coverage":c['covered_province_year_cells'],"floor_additional":need,"floor_final":eligible+need}))
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch",action="store_true",help="원본수집을제어하지않는60초간격읽기전용문서감시")
    parser.add_argument("--max-cycles",type=int,default=180)
    args = parser.parse_args()
    if not 1 <= args.max_cycles <= 180:
        raise ValueError("감시상한은최대180회/180분입니다")
    if not args.watch:
        main()
    else:
        # 이잠금은문서모니터전용이며collector/예산원장잠금을건드리지않는다.
        lock = ROOT / "evidence/integration/.collection-progress-monitor.lock"
        descriptor = os.open(lock,os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(descriptor,str(os.getpid()).encode())
        try:
            for cycle in range(args.max_cycles):
                evidence = main()
                running = evidence["running_evidence"]
                if evidence["budget"]["rate_limit_active"] or (not running["execution_lock_present"] and not running["pending_batches"]):
                    print(json.dumps({"monitor_stopped":True,"reason":"rate_limit_or_collector_no_longer_active","collector_control_action":False}),flush=True)
                    break
                if cycle+1 < args.max_cycles:
                    time.sleep(60)
        finally:
            os.close(descriptor)
            lock.unlink()
