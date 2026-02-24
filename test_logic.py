import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Mock missing dependencies before they are imported
mock_clob = MagicMock()
sys.modules["py_clob_client"] = mock_clob
sys.modules["py_clob_client.client"] = mock_clob
sys.modules["py_clob_client.clob_types"] = mock_clob
sys.modules["py_clob_client.constants"] = mock_clob
sys.modules["uvicorn"] = MagicMock()

class TestAddressLogic(unittest.TestCase):
    @patch("db.get_user_data")
    @patch("db.table")
    def test_duplicate_add_wallet(self, mock_table, mock_get_user_data):
        from db import add_wallet
        
        # Setup: address already exists
        mock_get_user_data.return_value = {
            "trackedWallets": ["0x123"]
        }
        
        result = add_wallet("user_1", "0x123")
        self.assertEqual(result, "duplicate")

    @patch("main.get_user_data")
    @patch("main.db_add_wallet")
    @patch("main.tracker")
    def test_address_limit_enforcement(self, mock_tracker, mock_add_wallet, mock_get_user_data):
        from main import add_wallet
        from fastapi import HTTPException
        
        # Case 1: Free user, 2 slots, adding 3rd
        mock_get_user_data.return_value = {
            "subscriptionStatus": "free",
            "trackedWallets": ["0x1", "0x2"],
            "extraSlots": 0
        }
        
        request = MagicMock()
        request.state.user_id = "user_1"
        
        import asyncio
        
        # Use simple try-except because add_wallet is async
        async def run_test():
            try:
                await add_wallet(request, "0x3")
                self.fail("Should have raised HTTPException 402")
            except HTTPException as e:
                self.assertEqual(e.status_code, 402)
                self.assertIn("limit reached", e.detail)

            # Case 2: Free user, purchased 1 extra slot, adding 3rd (allowed)
            mock_get_user_data.return_value = {
                "subscriptionStatus": "free",
                "trackedWallets": ["0x1", "0x2"],
                "extraSlots": 1
            }
            mock_add_wallet.return_value = True
            mock_tracker.tracked_addresses = ["0x1", "0x2"]
            
            res = await add_wallet(request, "0x3")
            self.assertEqual(res["message"], "Added wallet 0x3")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
