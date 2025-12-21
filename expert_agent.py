# expert_agent.py

import re
import json
from google.api_core.exceptions import ResourceExhausted

class ExpertAgent:
    """
    The "Expert" Agent (CORE). 
    A Neuro-Symbolic reasoning engine designed for dependency constraint optimization.
    """
    def __init__(self, llm_client):
        self.llm = llm_client
        self.llm_available = True

    def _clean_json_response(self, text: str) -> str:
        """Sanitizes LLM output to ensure valid JSON parsing."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        return cleaned.strip()

    def _extract_key_constraints(self, error_log: str) -> list:
        key_lines = []
        patterns = [
            r"^\s*([a-zA-Z0-9\-_]+.* requires .*)$",
            r"^\s*([a-zA-Z0-9\-_]+.* depends on .*)$",
            r"^\s*(The user requested .*)$",
            r"^\s*(Incompatible versions: .*)$",
            r"^\s*(Conflict: .*)$"
        ]
        for pat in patterns:
            for match in re.finditer(pat, error_log, re.MULTILINE):
                key_lines.append(match.group(1).strip())
        return list(set(key_lines))[:15]

    def summarize_error(self, error_message: str) -> str:
        """Generates a detailed summary including specific version numbers."""
        if not self.llm_available: return "(LLM summary unavailable)"
        
        key_constraints = self._extract_key_constraints(error_message)
        context = "\n".join(key_constraints) if key_constraints else error_message[:2500]

        prompt = (
            "Summarize the root cause of the dependency conflict in one sentence. "
            "CRITICAL: You MUST include the specific package versions mentioned in the log "
            "(e.g. 'pkgA==1.2 requires pkgB<2.0'). "
            f"Context: {context}"
        )
        try:
            return self.llm.generate_content(prompt).text.strip().replace('\n', ' ')
        except Exception:
            return "Failed to get summary from LLM."

    def diagnose_conflict_from_log(self, error_log: str) -> list[str]:
        """
        Extracts ALL conflicting package names using "Scorched Earth" Regex.
        """
        found_packages = set()
        
        # 1. Standard: "pkg==1.0", "pkg>=1.0"
        pattern_std = re.compile(r"(?P<name>[a-zA-Z0-9\-_]+)(?:==|>=|<=|~=|!=|<|>)")
        # 2. Loose: "pkg 1.0"
        pattern_loose = re.compile(r"(?P<name>[a-zA-Z0-9\-_]+)\s+\d+(?:\.\d+)+")
        # 3. Parentheses: "pkg (1.0)"
        pattern_paren = re.compile(r"(?P<name>[a-zA-Z0-9\-_]+)\s*\(\d+(?:\.\d+)+\)")

        for pat in [pattern_std, pattern_loose, pattern_paren]:
            for match in pat.finditer(error_log):
                name = match.group('name').lower()
                if self._is_valid_package_name(name): found_packages.add(name)

        # 4. Contextual Search
        context_keywords = [
            r"conflict(?:s)?\s+(?:between|among|with|in)\s+((?:[a-zA-Z0-9\-_]+(?:,?\s+and\s+|,?\s*)?)+)",
            r"requirement\s+((?:[a-zA-Z0-9\-_]+)+)",
        ]
        for keyword_pat in context_keywords:
            for match in re.finditer(keyword_pat, error_log, re.IGNORECASE):
                raw_list = match.group(1)
                tokens = re.split(r'[,\s]+', raw_list)
                for t in tokens:
                    clean_t = t.strip("`'").lower()
                    if self._is_valid_package_name(clean_t):
                        found_packages.add(clean_t)

        if '-' in found_packages: found_packages.remove('-')
        return list(found_packages)

    def _is_valid_package_name(self, name: str) -> bool:
        noise = {'python', 'pip', 'setuptools', 'wheel', 'setup', 'dependencies', 
                 'versions', 'requirement', 'conflict', 'between', 'and', 'the', 'version', 'package', 'for'}
        return name and len(name) > 1 and name not in noise

    def propose_co_resolution(
        self, 
        target_package: str, 
        error_log: str, 
        available_updates: dict,
        current_versions: dict = None,
        history: list = None
    ) -> dict | None:
        """
        Iterative Co-Resolution Planner with AURA Architecture Context.
        """
        if not self.llm_available: return None

        floor_constraints = json.dumps(current_versions, indent=2) if current_versions else "{}"
        ceiling_constraints = json.dumps(available_updates, indent=2)

        history_text = ""
        if history:
            history_text = "--- PREVIOUS FAILED ATTEMPTS (DO NOT REPEAT) ---\n"
            for i, (attempt_plan, failure_reason) in enumerate(history):
                history_text += f"Attempt {i+1} Plan: {attempt_plan}\nResult: FAILED. Reason: {failure_reason}\n\n"

        # --- THE ROBUST CONTEXT PROMPT ---
        prompt = f"""
        SYSTEM ROLE:
        You are the "Expert Agent" (CORE) within the AURA Framework.
        AURA is a hybrid agentic system for dependency management that uses a "Tiered Healing Strategy."
        
        CURRENT SITUATION:
        1. The "Manager Agent" identified a dependency deadlock involving '{target_package}'.
        2. It attempted a "Greedy Heuristic" (updating ALL involved packages to their maximum available versions).
        3. THE GREEDY ATTEMPT FAILED. 
        
        IMPLICATION:
        The failure of the Greedy Heuristic proves that "simply updating everything to max" is NOT the solution.
        There is likely a "Strict Pinning" conflict (e.g., PyTorch requiring a specific older NVIDIA driver) or a bounded constraint (e.g., "Requires Package < 2.0").
        
        YOUR MISSION:
        Analyze the conflict log below. Find a version combination that satisfies the graph.
        You will likely need to "hold back" one or more packages to an intermediate version (found in the error log constraints) rather than using the absolute latest from the Available Updates list.

        DATA CONTEXT:
        1. Target Package: {target_package}
        2. Current Versions (Floor): {floor_constraints}
        3. Available Updates (Ceiling): {ceiling_constraints}
        
        CONFLICT LOG (READ CAREFULLY):
        {error_log}

        {history_text}

        OUTPUT FORMAT:
        Reasoning: [Explain which constraint caused the Greedy failure and which package must be held back]
        ```json
        {{
            "plausible": true,
            "proposed_plan": ["package==version", ...]
        }}
        ```
        """

        try:
            response = self.llm.generate_content(prompt)
            clean_text = self._clean_json_response(response.text)
            
            # Robust JSON extraction
            match = re.search(r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL)
            if not match:
                match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            
            if not match: return None
            
            plan = json.loads(match.group(1))
            
            if plan.get("plausible") and isinstance(plan.get("proposed_plan"), list):
                valid_plan = []
                for requirement in plan.get("proposed_plan", []):
                    try:
                        pkg, ver = requirement.split('==')
                        # Check against Ceiling (Update) OR Floor (Hold Back)
                        # NOTE: We can relax this slightly if LLM finds a specific middle version in logs,
                        # but for safety, we stick to Floor/Ceiling validation.
                        if (pkg in available_updates and available_updates[pkg] == ver) or \
                           (current_versions and pkg in current_versions and current_versions[pkg] == ver):
                            valid_plan.append(requirement)
                    except ValueError: continue
                
                if not valid_plan: return {"plausible": False, "proposed_plan": []}
                plan["proposed_plan"] = valid_plan
                return plan
            return None
        except Exception:
            return None