# UX-Agent · menu inspection and order review

A local, instrumented mobile menu for the CEFET-MG HCI project. The application, experimental instructions, academic deliverables, and public help use Brazilian Portuguese. This repository contains synthetic calibration evidence for the deterministic policy R. The model adapters use real provider APIs.

The portable E2 Git bundle contains the complete local history. To inspect it in a fresh directory, run `git clone deliverables/E2_Repositorio_Git.bundle ux-agent`. The course submission requires a hosted Git URL with evaluator access. This workspace has no configured remote.

## Run locally

Use Python 3.10 or newer. The menu, runner, verifier and unit tests use the Python standard library. From the project root:

```powershell
python -m app.server --port 8765
```

Open [the local menu](http://127.0.0.1:8765/). Use a 360 × 800 CSS pixel viewport for the instrumented phone. The experimenter can inspect a magnified view, the permitted observation, actions and the event stream. C1 starts with an empty order. C2 starts with the sister's order already loaded. The review itself is opened by the first action of the reference method. The training menu has five items and separate instructions.

```powershell
python -m unittest discover -s tests -v
python -m agent.run --config R --task C1 --version A --seed 42 --out runs
python -m agent.run --config R --task C2 --version B --seed 42 --out runs
Get-ChildItem runs/logs/*.json | ForEach-Object { python -m verifier $_.FullName }
```

The last command recomputes task scores from the order and recorded facts. R has no language model. Its reference action count comes from a separate traversal at the measured starting zoom. Time stamps and unique session identifiers vary between replays. With the same local configuration and seed, the rule path and state metrics are reproducible.

## Model-backed pilot

For the full paired Gemini calibration, set `GEMINI_API_KEY` or save the key alone on one line in the Git-ignored `.env.gemini-key` file at the project root. The following commands show the planned conditions without a request and then run them.

```powershell
python -m tools.run_gemini_pilot --plan
python -m tools.run_gemini_pilot --check-key
python -m tools.run_gemini_pilot
```

The runner pairs C, P, P2 and P6 across C1/C2 and A/B using seed 42 and one model. Its default is `gemini-3.5-flash-lite`. Set `GEMINI_MODEL` or `--model` to select another model before the protocol is created. The key check queries model metadata without generation and prints only the provider's error codes. The runner spaces requests by at least six seconds at its default of ten requests per minute. Set `--rpm` to match the project's available throughput.

A transient network failure or HTTP 408, 429, 500, 502, 503, or 504 can trigger up to four retries of the same step. The runner applies exponential backoff, honors a feasible provider retry delay and logs each attempt separately. Set `--retries` and `--retry-base` to adjust the retry budget and initial backoff. Daily quotas, authentication errors and delays longer than the runner's two-minute wait limit end the session as technical failures. The existing per-action JSON rejection budget applies independently.

Outputs and per-request audit records go to `runs/E3_Gemini`. If all attempts fail, correct the underlying cause and run the same command again. Completed conditions are skipped, and the condition that ended in a technical failure starts from its original state with a new session ID. Earlier attempts remain archived.

After the runner stops, combine its actual sessions with the four reference runs. The supplemental ZIP records how many planned conditions ended without a technical failure.

```powershell
python tools/package_pilot.py --gemini-run runs/E3_Gemini
```

To follow the observed Gemini actions while the batch runs or inspect earlier steps, start `python -m tools.view_gemini` in a second terminal and open [the local Gemini record viewer](http://127.0.0.1:8766/). The viewer reads the audit files from disk. Use `--run` to inspect an alternative output folder. Executed events become available when a session writes its final log.

Set `GEMINI_API_KEY` and `GEMINI_MODEL` to a credential and the exact Gemini API model ID enabled on the account. Alternatively set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`. Set these in the environment of the shell that starts the process. The provider account must permit the selected model and structured JSON output. Each command can make a paid request per action and retry malformed choices twice. `--temperature` sets a provider-supported value. An omitted value uses the provider default. The local seed is always recorded. Gemini also receives a provider seed. Claude receives no seed parameter.

```powershell
python -m agent.run --config P --task C1 --version A --provider gemini --seed 42 --out runs
python -m agent.run --config C --task C1 --version A --provider gemini --seed 42 --out runs
python -m agent.run --config P2 --task C2 --version B --provider gemini --seed 42 --out runs
python -m agent.run --config P6 --task C2 --version B --provider gemini --seed 42 --out runs
python -m agent.run --config G --task C1 --version A --provider claude --seed 42 --out runs
```

For the complete calibration matrix with a single model and seed:

```powershell
foreach ($profile in 'P','P2','P6','C','G') {
    foreach ($task in 'C1','C2') {
        foreach ($version in 'A','B') {
            python -m agent.run --config $profile --task $task --version $version --provider gemini --seed 42 --out runs
        }
    }
}
```

The CLI rejects V1 and V2 before creating the application or contacting a provider. The application includes their initial states and operations. A future validation study requires a separately frozen protocol. There are no validation executions in the pilot. A provider failure is a technical interruption. Invalid proposals never mutate the order. The results for other profiles cannot be inferred from R.

## Components and data flow

| Location | Responsibility |
|---|---|
| `app/catalog.py` | Canonical domain content and literal task instructions from the previous submissions. Monetary values are integer cents. |
| `app/model.py`, `app/geometry.py` | MoLIC scene transitions, allowed state changes and positioned signs used by the browser and the runner. |
| `app/server.py` | Local browser interface for a participant and the researcher's demonstration. |
| `design/` | Help text, CTT, MoLIC, diagrams, sign parity and rationale. |
| `agent/configs/v1.json` | Versioned defaults and per-profile sampling distributions. |
| `agent/mechanisms/` | View clipping, FIFO memory, fragmentation, slip, review, scan strategy and impasse handling. |
| `agent/policies/` | R method and independent JSON-only policies for Gemini and Claude. |
| `agent/run.py` | Calibration guard, orchestration, closed event vocabulary, audit capture, archival and final call to the verifier. |
| `verifier/` | Order predicates and event analysis. Takes a completed log and imports no model adapter. |
| `tests/` | Synthetic unit fixtures, deterministic reference runs, and boundary checks. |
| `deliverables/` | IEEE papers, E1, E3, E5, citation checklist and independent audit. |

The model prompt consists of the visible projection, permitted actions, eligible FIFO fragments, the functional instruction, literal task wording and one training example. FIFO fragments can come from previously visited scenes if they entered the visible region earlier and remain in the buffer. G deliberately uses the entire rendered current scene as a generic baseline. The audit log also preserves the complete application state for the researcher. After each accepted action the interface emits its domain events. The verifier compares the order with the analyst's criteria independently of the policy.

## Profiles

| Profile | Initial zoom | Readability threshold | Scan strategy | Slip probability | Memory |
|---|---|---:|---|---:|---|
| P | Uniform [3, 5] | 3 | Linear | 0.05 | Uniform in {3, 4, 5} |
| P2 | Uniform [1.5, 2.5] | 1.5 | Linear 9/11, skipping 2/11 | 0.05 | Same |
| P6 | Uniform [5.5, 7] | 3 | Linear 9/11, skipping 2/11 | 0.05 | Same |
| C | 1 | 1 | Free | 0 | Same |
| G | 1 | 1 | Entire current page | 0 | Unlimited |
| R | 1 (or `--reference-zoom`) | 1 | Reference method | 0 | Rule-based |

P, P2, P6 and C share the same help threshold (five stagnant actions) and help probability (0.5). Capacity is paired by seed independently of the zoom draw. The scene's eligible signs and morphology control which actions are available. Each execution has a limit of 150 actions. Profiles can switch individual mechanisms off with repeatable `--disable M1` through `--disable M7`. Ablations belong to calibration. The configuration hash covers the sampled parameters, version, toggles and seed. Example:

```powershell
python -m agent.run --config P --task C2 --version A --seed 42 --disable M7 --out runs
```

## Measurements and interpretation

S requires both confirmation and a correct final order. A repaired error can coexist with success. Technical failures are reported separately. Give-up and limit events count as failures. E1–E6 distinguish selection, association, option/quantity, motor slip, review discrepancy and rule violations. A counts executed actions. R_A divides A by the independently measured reference length. D counts pan and zoom per located target. V measures revisits. O counts required signs missing before decision. U records help openings, access by layer and first access within the action sequence. An unobserved opportunity yields JSON null. The six MAC signatures are operational hypotheses. The pilot has no behavioral response times or human outcomes.

## Rebuild the academic package

The three IEEE documents share `deliverables/preambulo.tex`, `deliverables/referencias.bib` and vector material under `design/`. Edit the `institution` macro in the preamble to change the institutional line. Install Tectonic with access to its default TeX bundle, or an IEEEtran-capable TeX distribution. Run from the indicated directory so the relative inputs resolve.

```powershell
Push-Location deliverables
tectonic DesignUXAgent_IHC_Grupo_Amorim_Alvarenga_Cruz.tex
tectonic UXAgent_P3_Artigo_E4.tex
tectonic UXAgent_P3_Anexo_E1.tex
Pop-Location
python -m pip install reportlab
python tools/build_dictionary.py
python tools/package_pilot.py
python tools/freeze.py
```

The package builder recomputes the score of every included log, checks that all runs use C1/C2, regenerates the measured summary and verifies the ZIP CRC. The archive records when no requests were sent to a provider. See `deliverables/REFERENCIAS_PDF_CHECKLIST.md` for source files and `deliverables/E5_Roteiro_Demonstracao.md` for the live demonstration.

The instrument manifest hashes the exact application, policy, verifier, help and design files at packaging time. Run the final command to check a checkout against that snapshot. The manifest identifies the calibration instrument independently of each session's configuration hash. The researcher's visual console and synthetic unit fixtures can be demonstrated offline with `python -m agent.demo`. The human-facing F1 shortcut opens help and Escape returns when the scene supports it.

