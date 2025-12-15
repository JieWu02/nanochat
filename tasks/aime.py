"""
AIME 2024 evaluation.
https://huggingface.co/datasets/HuggingFaceH4/aime_2024

AIME (American Invitational Mathematics Examination) is a prestigious high school
mathematics competition with challenging problems. Each answer is an integer from 0 to 999.

Example problem instance:

Problem:
Every morning Aya goes for a 9-kilometer-long walk and stops at a coffee shop afterwards.
When she walks at a constant speed of s kilometers per hour, the walk takes her 4 hours,
including t minutes spent in the coffee shop. When she walks s+2 kilometers per hour,
the walk takes her 2 hours and 24 minutes, including t minutes spent in the coffee shop.
Suppose Aya walks at s+1/2 kilometers per hour. Find the number of minutes the walk takes
her, including the t minutes spent in the coffee shop.

Answer: 204
"""

import re
from datasets import load_dataset
from tasks.common import Task


def extract_answer(completion):
    """
    Extract a numerical answer (0-999) from the completion.

    AIME answers are always integers from 0 to 999.
    We look for patterns like:
    - "#### 204"
    - "The answer is 204"
    - "= 204"
    - Just a number at the end
    """
    if not completion:
        return None

    completion = completion.strip()

    # Pattern 1: GSM8K style "#### <number>"
    match = re.search(r"####\s*(\d+)", completion)
    if match:
        return match.group(1)

    # Pattern 2: "the answer is <number>" (case insensitive)
    match = re.search(r"(?:the\s+)?answer\s+is[:\s]*(\d+)", completion, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: "= <number>" at the end or followed by period/newline
    match = re.search(r"=\s*(\d+)\s*[.\n]?\s*$", completion)
    if match:
        return match.group(1)

    # Pattern 4: Boxed answer (LaTeX style) \boxed{204}
    match = re.search(r"\\boxed\{(\d+)\}", completion)
    if match:
        return match.group(1)

    # Pattern 5: Final number in the text (last resort)
    # Look for a standalone number (0-999) near the end
    matches = re.findall(r"\b(\d{1,3})\b", completion)
    if matches:
        # Return the last number found
        return matches[-1]

    return None


class AIME(Task):
    """
    AIME 2024 Task.

    AIME problems are challenging math competition problems where the answer
    is always an integer from 0 to 999.
    """

    def __init__(self, split="train", **kwargs):
        """
        Initialize the AIME 2024 task.

        Args:
            split: Dataset split (default "train" since AIME 2024 only has train split)
            **kwargs: Additional arguments passed to Task base class
        """
        super().__init__(**kwargs)
        assert split in ["train"], "AIME 2024 only has 'train' split"
        self.ds = load_dataset("HuggingFaceH4/aime_2024", split=split)

    @property
    def eval_type(self):
        return 'generative'

    def num_examples(self):
        return len(self.ds)

    def get_example(self, index):
        """
        Get a single problem from the dataset.

        Returns a conversation dict with:
        - messages: list of user/assistant messages
        - The user message contains the problem
        - The assistant message contains the answer (for ground truth)
        """
        row = self.ds[index]
        problem = row['problem']  # The problem statement
        answer = row['answer']    # The numerical answer (string, e.g., "204")

        # Format the problem with clear instructions
        user_message = (
            f"Solve this math problem. Give your final answer as a single integer from 0 to 999.\n\n"
            f"Problem: {problem}\n\n"
            f"Show your work step by step, then give your final answer in the format: #### <answer>"
        )

        # Create the conversation
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": f"#### {answer}"},
        ]

        conversation = {
            "messages": messages,
            "answer": answer,  # Store for easy access during evaluation
        }

        return conversation

    def evaluate(self, conversation, assistant_response):
        """
        Evaluate the assistant's response.

        Args:
            conversation: The conversation dict containing the ground truth
            assistant_response: The model's generated response (string)

        Returns:
            1 if correct, 0 if incorrect
        """
        assert isinstance(assistant_response, str), "Expecting string response"

        # Get ground truth answer
        ground_truth = conversation.get('answer')
        if ground_truth is None:
            # Fallback: extract from assistant message
            assistant_message = conversation['messages'][-1]['content']
            ground_truth = extract_answer(assistant_message)

        # Extract predicted answer
        predicted = extract_answer(assistant_response)

        # Compare answers
        if ground_truth is None or predicted is None:
            return 0

        # Normalize: remove leading zeros and compare
        try:
            gt_int = int(ground_truth)
            pred_int = int(predicted)
            is_correct = int(gt_int == pred_int)
        except ValueError:
            is_correct = 0

        return is_correct

    def reward(self, conversation, assistant_response):
        """
        Compute reward for RL training.

        For AIME, we use binary reward based on correctness.
        """
        is_correct = self.evaluate(conversation, assistant_response)
        return float(is_correct)
