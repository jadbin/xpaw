# coding=utf-8

from xpaw.ds import PriorityQueue


class TestPriorityQueue:
    def test_len(self):
        q = PriorityQueue(2)
        op = [(0, 0, False),
              (1, "A", 1),
              (0, 1, False),
              (1, "B", 2),
              (0, 2, True),
              (1, "C", 3),
              (0, 2, True),
              (-1,),
              (0, 1, False),
              (-1,),
              (0, 0, False),
              (-1,),
              (0, 0, False)]
        for i in op:
            if i[0] == 0:
                assert len(q) == i[1] and q.is_full() == i[2]
            elif i[0] == 1:
                q.push(i[1], i[2])
            elif i[0] == -1:
                q.pop()
            else:
                raise RuntimeError("Unexpected operation: %s" % i[0])

    def test_push_and_pop_top(self):
        q = PriorityQueue(5)
        # 0: check, 1: insert, -1: delete
        op = [(0, None),
              (1, "A", 2),
              (0, "A"),
              (1, "B", 1),
              (0, "A"),
              (1, "C", 3),
              (0, "C"),
              (1, "D", 5),
              (0, "D"),
              (-1,),
              (0, "C"),
              (1, "D", 5),
              (0, "D"),
              (1, "E", 4),
              (0, "D"),
              (1, "F", 6),
              (0, "D"),
              (-1,),
              (0, "E"),
              (-1,),
              (0, "C"),
              (-1,),
              (0, "A"),
              (1, "G", 9),
              (0, "G"),
              (1, "H", 8),
              (0, "G"),
              (-1,),
              (0, "H"),
              (-1,),
              (0, "A"),
              (-1,),
              (0, "B"),
              (-1,),
              (0, None),
              (-1,),
              (0, None)]
        for i in op:
            if i[0] == 0:
                if i[1] is None:
                    assert q.top() is None
                else:
                    assert q.top() == i[1]
            elif i[0] == 1:
                q.push(i[1], i[2])
            elif i[0] == -1:
                q.pop()
            else:
                raise RuntimeError("Unexpected operation: %s" % i[0])

    def test_push_and_pop_index(self):
        q = PriorityQueue(5)
        # 0: check, 1: insert, -1: delete
        op = [(0, None),
              (1, "A", 2),
              (0, "A"),
              (1, "B", 1),
              (0, "A"),
              (1, "C", 3),
              (0, "C"),
              (1, "D", 5),
              (0, "D"),
              (-1, "D"),
              (0, "C"),
              (1, "D", 5),
              (0, "D"),
              (1, "E", 4),
              (0, "D"),
              (1, "F", 6),
              (0, "D"),
              (-1, "C"),
              (0, "D"),
              (-1, "D"),
              (0, "E"),
              (-1, "B"),
              (0, "E"),
              (1, "G", 9),
              (0, "G"),
              (1, "H", 8),
              (-1, "H"),
              (0, "G"),
              (-1, "G"),
              (0, "E"),
              (-1, "E"),
              (0, "A"),
              (-1, "A"),
              (0, None)]
        index = {}
        for i in op:
            if i[0] == 0:
                if i[1] is None:
                    assert q.top() is None
                else:
                    assert q.top() == i[1]
            elif i[0] == 1:
                index[i[1]] = q.push(i[1], i[2])
            elif i[0] == -1:
                q.pop(index[i[1]])
                index.pop(i[1])
            else:
                raise RuntimeError("Unexpected operation: %s" % i[0])
