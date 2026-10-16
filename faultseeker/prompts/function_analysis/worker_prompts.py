"""
Function Call Analysis Prompts

Prompts for analyzing function calls in the function validation workflow.
These prompts handle function call selection, processing, organization, and filtering.
"""

from dataclasses import dataclass


@dataclass
class WorkerPrompts:
    """Prompts for function call analysis workflow"""

    function_call_task_selection: str = """Given the task tree and the current analysis, select one sub-task that is favorable and most likely to lead to successful fault localization. Pay more attention to analyze function calls with unusual params or function calls with unusual high occurrence (characteristics pointed to vulnerabilities like reentrancy, insufficient validations, and other contract related vulnerabilities), or risky function calls (functions related to price calculation) or customized business logic). Pay attention to function calls with high frequency as well.
Task tree: {task_tree}
Function Call Information (FCI): {function_call_info_summary}
Current understanding: {current_understanding}

Return ONLY a valid JSON object with these exact keys — no markdown, no explanation:
{{
  "task_selected": "<sub-task number>",
  "task_description": "<detailed steps to complete the selected sub-task>",
  "information": "<selected information from the FCI required to complete the subtask>",
  "additional_information": "<additional information required but not in FCI, or empty string>"
}}"""


    function_call_task_generation: str = """Given the task tree and the current analysis, select one sub-task that is favorable and most likely to lead to successful fault localization.\nTask tree: {task_tree}\n
Function call information: {function_call_info_summary}\n
Return the detailed task description with the part of information to be further invesitgated.
    """

    function_call_info_processing: str = """Below is the task and the inforamtion to be analyzed. Keep the analysis result concise while keeping all the key point.\nTask and information provided: {selected_task}"""

    function_call_organization_function_call: str = """Given the function call information, please understand and summarize the current understanding to the transaction regarding fault localization. Keep the summary concise while keeping all the key point.\nFunction call information provided: {function_call_info_summary}"""

    function_call_organization_after_task_completion: str = """Given the current understanding and the new analysis result for the selected, please understand and update the understanding of the transaction. Keep the summary concise while keeping all the key point. \nCurrent understanding:{current_understanding}\nTask and information provided: {selected_task}"""

    function_call_children_call_filtering: str = """Given the function call information and its related children calls, please complete the task described at the start. Return the index of the function calls to be further investigated in a list or [] if no functions need to be further investigated. Do not include further explanations.\nParent function name: {function_name}\nChildren calls: {children_calls}"""

    retrieve_additional_info: str = '''Return only a JSON object with these optional keys: function_call (singular), children_calls, source_code, balance_change. Never use function_calls. The first three fields must be lists of objects with exactly address and function keys; balance_change must be a list of full addresses. For unavailable or unneeded information, omit the field or use []. Never use "" or null for these fields. Address means a 0x-prefixed 20-byte contract address (42 characters). A four-byte function selector is not an address: it belongs in function. observed_entry_functions_at_address explicitly lists functions entering their owner contract; observed_child_calls contains actual outgoing child identities and paths. Use only full owners present in the available call information. Never guess an owner, reinterpret a selector as an address, substitute an unresolved variable alias, or copy a schema illustration as evidence. Omit unresolved references and return {} if no supported request resolves.'''


    function_analysis_init_prompt: str = """The information of target function call is summarized as below. Please follow the instruction and update the task tree. The current task tree is as follows: {task_tree}\nCurrent understanding of the transaction:{current_understanding}\nInformation of the function call: {function_call_info_summary}"""

    check_analysis_adequacy: str = """Given the current understanding of the transaction, please decide if the analysis of the function call and its children calls is adequate for fault localization to move to the next functions to be investigated. Return Yes/No only. Do not include any other information."""

    check_analysis_adequacy_alt: str = """Given the current understanding of the transaction, please decide if the analysis of current function and its children calls is adequate to move to the next functions to be inspected. Return Yes/No only. Do not include any other information."""

    narrow_down_functions: str = '''You are a senior smart contract security expert and helping with a fault localization analysis for a malicious transaction. Given the information of the following function calls that have been selected to be potentially related to the fault (e.g., related to price manipulation, key transfer/stake/unstake/other token related operations, or key validations, same functions with multiple addresses), your task is to understand the provided information and narrow down the list of functions to be inspected by identifying and deciding which functions are most likely containing the fault implementation. Note that functions explicitly mentioned price related operations such as cache must be kept. The function call information is as follows (value for each is its appearance count): {function_call_to_be_inspected}\nReturn only a nonempty strict JSON array of unique strings in square brackets. Each string must be copied exactly from a key in the provided function call information, preserving the complete function_name_address key. Do not return bare selectors or keys with missing owners. Format illustration only, not a valid selection: ["<complete supplied function_name_address key>"]. Never output that placeholder. Do not return a set, an object, markdown, or extra text. Try to narrow down the list as much as possible.'''

    narrow_down_functions_with_created_contracts: str = '''You are a senior smart contract security expert and helping with a fault localization analysis for a malicious transaction. Given the information of the following function calls that have been selected to be potentially related to the fault, your task is to understand the provided information and narrow down the list of functions to be inspected by identifying and deciding which functions are most likely containing the fault implementation. The function call information is as follows: {function_call_to_be_inspected}\nReturn only a nonempty strict JSON array of unique strings in square brackets. Each string must be copied exactly from a key in the provided function call information. These keys are function names; do not append an address. Format illustration only, not a valid selection: ["<supplied function key>"]. Never output that placeholder. Do not return a set, an object, markdown, or extra text. Try to narrow down the list as much as possible.'''
