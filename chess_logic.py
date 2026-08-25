import re

class Board:
    def __init__(self):
        self.reset()

    def reset(self):
        # 8x8 board: None or (color, piece_type)
        # color: 'w' or 'b'
        # piece_type: 'P', 'N', 'B', 'R', 'Q', 'K'
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.turn = 'w'
        self.castling = 'KQkq'
        self.ep_square = None
        self.halfmove = 0
        self.fullmove = 1
        self.load_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def load_fen(self, fen):
        parts = fen.split()
        placement = parts[0]
        self.turn = parts[1]
        self.castling = parts[2]
        self.ep_square = parts[3] if parts[3] != '-' else None
        self.halfmove = int(parts[4])
        self.fullmove = int(parts[5])

        # Clear board
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        rows = placement.split('/')
        for r_idx, row in enumerate(rows):
            grid_row = 7 - r_idx
            col = 0
            for char in row:
                if char.isdigit():
                    col += int(char)
                else:
                    color = 'w' if char.isupper() else 'b'
                    p_type = char.upper()
                    self.grid[grid_row][col] = (color, p_type)
                    col += 1

    def to_fen(self):
        rows = []
        for r in range(7, -1, -1):
            row_str = ""
            empty_count = 0
            for c in range(8):
                piece = self.grid[r][c]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    color, p_type = piece
                    char = p_type if color == 'w' else p_type.lower()
                    row_str += char
            if empty_count > 0:
                row_str += str(empty_count)
            rows.append(row_str)
        
        placement = "/".join(rows)
        ep = self.ep_square if self.ep_square else "-"
        return f"{placement} {self.turn} {self.castling} {ep} {self.halfmove} {self.fullmove}"

    @staticmethod
    def sq_to_coords(sq):
        return ord(sq[0]) - ord('a'), int(sq[1]) - 1

    @staticmethod
    def coords_to_sq(c, r):
        return chr(ord('a') + c) + str(r + 1)

    def get_piece(self, sq):
        c, r = self.sq_to_coords(sq)
        return self.grid[r][c]

    def parse_pgn_moves(self, pgn_text):
        # Remove PGN headers enclosed in square brackets [...]
        pgn = re.sub(r'\[.*?\]', '', pgn_text)
        # Remove comments, evaluations, move numbers
        # Comments like { ... } or ; ...
        pgn = re.sub(r'\{.*?\}', '', pgn)
        pgn = re.sub(r';.*?\n', '\n', pgn)
        # Move numbers like 1. e4 or 1... e5 or 12.
        pgn = re.sub(r'\d+\.+\s*', ' ', pgn)
        # Results like 1-0, 0-1, 1/2-1/2, *
        pgn = re.sub(r'(1-0|0-1|1/2-1/2|\*)', '', pgn)
        # Tokenize moves
        moves = [m.strip() for m in pgn.split() if m.strip()]
        return moves

    def get_pseudo_legal_moves(self, c, r):
        piece = self.grid[r][c]
        if not piece:
            return []
        color, p_type = piece
        moves = []

        if p_type == 'P':
            direction = 1 if color == 'w' else -1
            start_row = 1 if color == 'w' else 6
            # Single push
            nr = r + direction
            if 0 <= nr < 8 and self.grid[nr][c] is None:
                moves.append((c, nr))
                # Double push
                nnr = r + 2 * direction
                if r == start_row and self.grid[nnr][c] is None:
                    moves.append((c, nnr))
            # Captures
            for dc in [-1, 1]:
                nc = c + dc
                if 0 <= nc < 8 and 0 <= nr < 8:
                    target = self.grid[nr][nc]
                    if target and target[0] != color:
                        moves.append((nc, nr))
                    elif self.ep_square:
                        ep_c, ep_r = self.sq_to_coords(self.ep_square)
                        if nc == ep_c and nr == ep_r:
                            moves.append((nc, nr))

        elif p_type == 'N':
            offsets = [(1,2), (2,1), (1,-2), (2,-1), (-1,2), (-2,1), (-1,-2), (-2,-1)]
            for dc, dr in offsets:
                nc, nr = c + dc, r + dr
                if 0 <= nc < 8 and 0 <= nr < 8:
                    target = self.grid[nr][nc]
                    if target is None or target[0] != color:
                        moves.append((nc, nr))

        elif p_type == 'B' or p_type == 'R' or p_type == 'Q':
            directions = []
            if p_type == 'B' or p_type == 'Q':
                directions.extend([(1,1), (1,-1), (-1,1), (-1,-1)])
            if p_type == 'R' or p_type == 'Q':
                directions.extend([(1,0), (-1,0), (0,1), (0,-1)])

            for dc, dr in directions:
                nc, nr = c + dc, r + dr
                while 0 <= nc < 8 and 0 <= nr < 8:
                    target = self.grid[nr][nc]
                    if target is None:
                        moves.append((nc, nr))
                    elif target[0] != color:
                        moves.append((nc, nr))
                        break
                    else:
                        break
                    nc += dc
                    nr += dr

        elif p_type == 'K':
            for dc in [-1, 0, 1]:
                for dr in [-1, 0, 1]:
                    if dc == 0 and dr == 0:
                        continue
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < 8 and 0 <= nr < 8:
                        target = self.grid[nr][nc]
                        if target is None or target[0] != color:
                            moves.append((nc, nr))

        return moves

    def parse_san(self, san):
        """Converts SAN move (like Nf3, exd5, O-O) to coordinate string (like g1f3, e4d5, e1g1)"""
        # Clean SAN
        san_clean = san.replace('+', '').replace('#', '').replace('?', '').replace('!', '').strip()

        # Handle castling
        if san_clean == 'O-O':
            if self.turn == 'w':
                return 'e1g1'
            else:
                return 'e8g8'
        elif san_clean == 'O-O-O':
            if self.turn == 'w':
                return 'e1c1'
            else:
                return 'e8c8'

        # Match regular moves
        # E.g. exd5, Nf3, Nfd2, R1e2, Qh4xe1, e8=Q
        match = re.match(r'^([NBRQK])?([a-h])?([1-8])?(x)?([a-h][1-8])(=?[NBRQK])?$', san_clean)
        if not match:
            raise ValueError(f"Could not parse SAN move: {san}")

        p_char, src_file, src_rank, is_capture, dest, promo = match.groups()
        p_type = p_char if p_char else 'P'
        dest_c, dest_r = self.sq_to_coords(dest)

        # Find matching pieces
        candidates = []
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece and piece[0] == self.turn and piece[1] == p_type:
                    # Check if this piece can move to dest
                    possible_destinations = self.get_pseudo_legal_moves(c, r)
                    if (dest_c, dest_r) in possible_destinations:
                        # Check hints
                        if src_file and chr(ord('a') + c) != src_file:
                            continue
                        if src_rank and str(r + 1) != src_rank:
                            continue
                        candidates.append((c, r))

        if len(candidates) == 0:
            raise ValueError(f"No legal candidate pieces found for {san} in board position {self.to_fen()}")
        elif len(candidates) > 1:
            raise ValueError(f"Ambiguous SAN move {san}: found multiple candidates {candidates} in position {self.to_fen()}")

        src_c, src_r = candidates[0]
        src_sq = self.coords_to_sq(src_c, src_r)
        
        promo_suffix = ""
        if promo:
            promo_suffix = promo.replace('=', '').lower()

        return f"{src_sq}{dest}{promo_suffix}"

    def make_move(self, uci_move):
        """Applies a UCI coordinate move (like e2e4, e7e8q) to the board state"""
        src = uci_move[:2]
        dest = uci_move[2:4]
        promo = uci_move[4:] if len(uci_move) > 4 else None

        src_c, src_r = self.sq_to_coords(src)
        dest_c, dest_r = self.sq_to_coords(dest)
        
        piece = self.grid[src_r][src_c]
        if not piece:
            return

        color, p_type = piece

        # Handle castling
        if p_type == 'K' and abs(dest_c - src_c) == 2:
            # Move Rook too
            if dest_c == 6: # King-side
                rook_src_c, rook_dest_c = 7, 5
            else: # Queen-side
                rook_src_c, rook_dest_c = 0, 3
            self.grid[src_r][rook_dest_c] = self.grid[src_r][rook_src_c]
            self.grid[src_r][rook_src_c] = None

        # Handle en passant capture
        if p_type == 'P' and dest == self.ep_square:
            capture_r = src_r
            capture_c = dest_c
            self.grid[capture_r][capture_c] = None

        # Move the piece
        target_piece = (color, promo.upper()) if promo else piece
        self.grid[dest_r][dest_c] = target_piece
        self.grid[src_r][src_c] = None

        # Update en passant target square
        self.ep_square = None
        if p_type == 'P' and abs(dest_r - src_r) == 2:
            self.ep_square = self.coords_to_sq(src_c, (src_r + dest_r) // 2)

        # Update castling rights
        # If King moves
        if p_type == 'K':
            if color == 'w':
                self.castling = self.castling.replace('K', '').replace('Q', '')
            else:
                self.castling = self.castling.replace('k', '').replace('q', '')
        # If Rook moves or is captured
        elif p_type == 'R':
            if color == 'w':
                if src_c == 7 and src_r == 0:
                    self.castling = self.castling.replace('K', '')
                elif src_c == 0 and src_r == 0:
                    self.castling = self.castling.replace('Q', '')
            else:
                if src_c == 7 and src_r == 7:
                    self.castling = self.castling.replace('k', '')
                elif src_c == 0 and src_r == 7:
                    self.castling = self.castling.replace('q', '')
                    
        # If rooks are captured at their starting squares
        if dest_c == 7 and dest_r == 0:
            self.castling = self.castling.replace('K', '')
        elif dest_c == 0 and dest_r == 0:
            self.castling = self.castling.replace('Q', '')
        elif dest_c == 7 and dest_r == 7:
            self.castling = self.castling.replace('k', '')
        elif dest_c == 0 and dest_r == 7:
            self.castling = self.castling.replace('q', '')

        if self.castling == "":
            self.castling = "-"

        # Update counters
        if p_type == 'P' or self.grid[dest_r][dest_c] is not None:
            self.halfmove = 0
        else:
            self.halfmove += 1

        if self.turn == 'b':
            self.fullmove += 1
            self.turn = 'w'
        else:
            self.turn = 'b'

if __name__ == "__main__":
    # Simple self-test
    b = Board()
    print("Initial FEN:", b.to_fen())
    
    # Test e4
    uci = b.parse_san("e4")
    print("SAN e4 -> UCI:", uci)
    b.make_move(uci)
    
    # Test Nf6
    uci = b.parse_san("Nf6")
    print("SAN Nf6 -> UCI:", uci)
    b.make_move(uci)
    print("FEN after e4 Nf6:", b.to_fen())
