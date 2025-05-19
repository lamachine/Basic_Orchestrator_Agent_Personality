from unittest.mock import patch

import pytest

from other_files_future_use.cli_old import main


def test_cli_start_new_conversation():
    with (
        patch("builtins.input", side_effect=["1", "exit"]),
        patch("builtins.print") as mock_print,
    ):
        main()

        # Check if the CLI prompts for conversation options
        mock_print.assert_any_call("\nConversation options:")
        mock_print.assert_any_call("1. Start a new conversation")
        mock_print.assert_any_call("2. Continue an existing conversation")


def test_cli_continue_conversation():
    with (
        patch("builtins.input", side_effect=["2", "n", "exit"]),
        patch("builtins.print") as mock_print,
    ):
        main()

        # Check if the CLI handles continuing a conversation
        mock_print.assert_any_call("No existing conversations found. Starting a new one.")


def test_cli_invalid_input():
    with (
        patch("builtins.input", side_effect=["invalid", "exit"]),
        patch("builtins.print") as mock_print,
    ):
        main()

        # Check if the CLI handles invalid input gracefully
        mock_print.assert_any_call("Invalid input. Starting a new conversation.")
