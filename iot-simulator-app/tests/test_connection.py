import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.client import OfflineBufferQueue

class TestOfflineBuffer(unittest.TestCase):

    def setUp(self):
        self.buffer = OfflineBufferQueue(max_records=10)
        self.buffer.clear()

    def tearDown(self):
        self.buffer.clear()

    def test_enqueue_and_dequeue(self):
        self.assertEqual(self.buffer.pending_count, 0)
        item1 = {"msg": "sample_1"}
        item2 = {"msg": "sample_2"}

        self.buffer.enqueue(item1)
        self.buffer.enqueue(item2)
        self.assertEqual(self.buffer.pending_count, 2)

        batch = self.buffer.dequeue_batch(batch_size=1)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["msg"], "sample_1")
        self.assertEqual(self.buffer.pending_count, 1)

    def test_bounded_limit(self):
        for i in range(15):
            self.buffer.enqueue({"msg": f"sample_{i}"})
        
        # Max capacity is 10
        self.assertEqual(self.buffer.pending_count, 10)

if __name__ == "__main__":
    unittest.main()
