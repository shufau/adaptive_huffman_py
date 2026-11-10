NYT_SYMBOL = -1
INTERNAL_SYMBOL = -2

class Node:
    __slots__ = ['weight', 'parent', 'left', 'right', 'symbol']
    
    def __init__(self, weight=0, parent=0, left=0, right=0, symbol=0):
        self.weight = weight
        self.parent = parent
        self.left = left
        self.right = right
        self.symbol = symbol

class AdaptiveHuffman:
    def __init__(self):
        # 分配 514 個節點。索引 0 作為 null 指標，1~513 作為有效節點
        # 256 個字元最多會產生 256 個葉節點 + 255 個內部節點 = 511 個節點
        self.nodes = [Node() for _ in range(514)]
        
        # 初始狀態下，根節點就是 NYT 節點
        self.nodes[513].symbol = NYT_SYMBOL
        
        self.nyt_index = 513
        self.root_index = 513
        self.map = [0] * 256  # 紀錄 ASCII 字元對應的葉節點索引

    def swap_nodes(self, a: int, b: int):
        pa = self.nodes[a].parent
        pb = self.nodes[b].parent
        
        # 1. 交換陣列中兩節點的資料內容
        self.nodes[a], self.nodes[b] = self.nodes[b], self.nodes[a]
        
        # 2. 恢復兩陣列位置對應的父節點指標
        self.nodes[a].parent = pa
        self.nodes[b].parent = pb
        
        # 3. 更新被移到位置 a 的節點，其子節點的父指標
        a_left = self.nodes[a].left
        if a_left != 0: self.nodes[a_left].parent = a
        a_right = self.nodes[a].right
        if a_right != 0: self.nodes[a_right].parent = a
        
        # 4. 更新被移到位置 b 的節點，其子節點的父指標
        b_left = self.nodes[b].left
        if b_left != 0: self.nodes[b_left].parent = b
        b_right = self.nodes[b].right
        if b_right != 0: self.nodes[b_right].parent = b
        
        # 5. 更新字元映射表與 NYT 索引
        if self.nodes[a].symbol >= 0: self.map[self.nodes[a].symbol] = a
        if self.nodes[b].symbol >= 0: self.map[self.nodes[b].symbol] = b
        if self.nodes[a].symbol == NYT_SYMBOL: self.nyt_index = a
        if self.nodes[b].symbol == NYT_SYMBOL: self.nyt_index = b

    def update(self, node: int):
        while node != 0:  # 直到走到根節點之上 (null)
            max_idx = node
            
            # 找出相同權重中，隱含編號最大（也就是索引最大）的節點
            for i in range(node + 1, 514):
                if self.nodes[i].weight == self.nodes[node].weight:
                    max_idx = i
                elif self.nodes[i].weight > self.nodes[node].weight:
                    break  # 陣列維持按權重排序，提早結束
            
            # 如果找到的節點不是自己，也不是自己的父節點，就進行交換
            if max_idx != node and max_idx != self.nodes[node].parent:
                self.swap_nodes(node, max_idx)
                node = max_idx
                
            self.nodes[node].weight += 1
            node = self.nodes[node].parent

    def add_symbol(self, symbol: int):
        nyt = self.nyt_index
        left = nyt - 2   # 新的 NYT
        right = nyt - 1  # 新的字元葉節點
        
        # 設定新的 NYT
        self.nodes[left].symbol = NYT_SYMBOL
        self.nodes[left].weight = 0
        self.nodes[left].parent = nyt
        self.nodes[left].left = 0
        self.nodes[left].right = 0
        
        # 設定新的字元葉節點
        self.nodes[right].symbol = symbol
        self.nodes[right].weight = 0
        self.nodes[right].parent = nyt
        self.nodes[right].left = 0
        self.nodes[right].right = 0
        
        # 舊的 NYT 變成內部節點
        self.nodes[nyt].symbol = INTERNAL_SYMBOL
        self.nodes[nyt].left = left
        self.nodes[nyt].right = right
        
        self.nyt_index = left
        self.map[symbol] = right
        
        # 從新的字元葉節點開始向上更新權重
        self.update(right)

    def get_path(self, node: int) -> list:
        path = []
        while self.nodes[node].parent != 0:
            p = self.nodes[node].parent
            if self.nodes[p].left == node:
                path.append(0)
            else:
                path.append(1)
            node = p
        path.reverse()  # 從下往上找，最後需要反轉
        return path


class BitWriter:
    def __init__(self):
        self.bytes = bytearray()
        self.current_byte = 0
        self.bit_count = 0

    def write_bit(self, bit: int):
        if bit != 0:
            self.current_byte |= (1 << (7 - self.bit_count))
        self.bit_count += 1
        if self.bit_count == 8:
            self.bytes.append(self.current_byte)
            self.current_byte = 0
            self.bit_count = 0

    def write_path(self, path: list):
        for bit in path:
            self.write_bit(bit)

    def write_bits(self, value: int, count: int):
        for i in range(count - 1, -1, -1):
            bit = (value >> i) & 1
            self.write_bit(bit)

    def flush(self) -> bytearray:
        if self.bit_count > 0:
            self.bytes.append(self.current_byte)
        return self.bytes


class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.byte_index = 0
        self.bit_index = 0

    def read_bit(self) -> int:
        if self.byte_index >= len(self.data):
            raise EOFError("Unexpected end of bit stream")
        
        bit = (self.data[self.byte_index] >> (7 - self.bit_index)) & 1
        self.bit_index += 1
        if self.bit_index == 8:
            self.bit_index = 0
            self.byte_index += 1
        return bit

    def read_bits(self, count: int) -> int:
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value


def core_compress(input_data: bytes) -> bytearray:
    writer = BitWriter()
    tree = AdaptiveHuffman()

    for byte in input_data:
        node_idx = tree.map[byte]
        if node_idx != 0:
            # 字元已存在，輸出路徑並更新樹
            path = tree.get_path(node_idx)
            writer.write_path(path)
            tree.update(node_idx)
        else:
            # 新字元，輸出 NYT 路徑 -> 原字元 -> 擴展樹
            path = tree.get_path(tree.nyt_index)
            writer.write_path(path)
            writer.write_bits(byte, 8)
            tree.add_symbol(byte)
            
    return writer.flush()


def core_decompress(input_data: bytes, original_len: int) -> bytearray:
    reader = BitReader(input_data)
    output = bytearray()

    if original_len == 0:
        return output

    tree = AdaptiveHuffman()

    # 處理第一個原始字元
    first_byte = reader.read_bits(8)
    output.append(first_byte)
    tree.add_symbol(first_byte)

    while len(output) < original_len:
        curr = tree.root_index
        
        # 往下走訪樹，直到抵達葉節點
        while tree.nodes[curr].left != 0 and tree.nodes[curr].right != 0:
            bit = reader.read_bit()
            if bit == 0:
                curr = tree.nodes[curr].left
            else:
                curr = tree.nodes[curr].right

        if tree.nodes[curr].symbol == NYT_SYMBOL:
            # 抵達 NYT 節點，讀取接下來的 8 bits
            new_byte = reader.read_bits(8)
            output.append(new_byte)
            tree.add_symbol(new_byte)
        else:
            # 抵達已知字元節點
            sym = tree.nodes[curr].symbol
            output.append(sym)
            tree.update(curr)

    return output


def compress_data(input_data: bytes) -> bytes:
    """外部呼叫：壓縮資料並加上檔頭"""
    if not input_data:
        return bytes([0x00])

    compressed_body = core_compress(input_data)
    orig_len = len(input_data)
    
    result = bytearray()
    
    # 判斷壓縮後是否反而變大
    if len(compressed_body) >= len(input_data):
        result.append(0x00) # 0x00 代表無壓縮
        result.extend(orig_len.to_bytes(4, byteorder='little'))
        result.extend(input_data)
    else:
        result.append(0x01) # 0x01 代表已壓縮
        result.extend(orig_len.to_bytes(4, byteorder='little'))
        result.extend(compressed_body)
        
    return bytes(result)


def decompress_data(input_data: bytes) -> bytes:
    """外部呼叫：解析檔頭並解壓縮資料"""
    if len(input_data) < 5:
        return bytes()

    flag = input_data[0]
    orig_len = int.from_bytes(input_data[1:5], byteorder='little')
    payload = input_data[5:]

    if flag == 0x00:
        return payload[:min(orig_len, len(payload))]

    try:
        return bytes(core_decompress(payload, orig_len))
    except EOFError:
        return payload  # 解碼失敗時退回原始 payload (與原版行為一致)