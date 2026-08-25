import subprocess
import os
import re
import math

class StockfishHelper:
    def __init__(self, binary_path="./stockfish/stockfish-macos-m1-apple-silicon"):
        self.binary_path = os.path.abspath(binary_path)

    def analyze_position(self, moves, depth=10, active_color='w'):
        """
        Sends the move sequence to Stockfish and gets the evaluation from White's perspective.
        Returns:
            score_pawns: Float (e.g. +0.35 or -1.2) or 'mate_in_X'
            sigmoid_percentage: Float in [0, 1] (0.5 is equal, 1.0 is white winning, 0.0 is black winning)
        """
        try:
            # Launch Stockfish
            process = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            print(f"Failed to launch Stockfish: {e}")
            return 0.0, 0.5

        # Initialize UCI
        process.stdin.write("uci\n")
        process.stdin.write("isready\n")
        
        # Set position
        moves_str = " ".join(moves)
        if moves_str:
            process.stdin.write(f"position startpos moves {moves_str}\n")
        else:
            process.stdin.write("position startpos\n")
            
        # Start analysis
        process.stdin.write(f"go depth {depth}\n")
        process.stdin.flush()

        bestmove_found = False
        score_type = "cp"
        score_val = 0

        # Read lines
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            
            # Look for bestmove to stop
            if line.startswith("bestmove"):
                bestmove_found = True
                break

            # Parse score from info depth
            if line.startswith("info depth") and "score" in line:
                # Find score part
                match = re.search(r'score (cp|mate) (-?\d+)', line)
                if match:
                    score_type = match.group(1)
                    score_val = int(match.group(2))

        # Terminate process cleanly
        try:
            process.stdin.write("quit\n")
            process.stdin.flush()
            process.terminate()
        except:
            pass

        # Calculate score from White's perspective
        # If it's Black's turn to move, Stockfish score is from Black's perspective, so invert it
        if active_color == 'b':
            score_val = -score_val

        # Convert to pawn units
        if score_type == "cp":
            pawns = score_val / 100.0
        else: # mate
            # If mate is positive, it means active side wins. Capped at +/- 10 pawns
            pawns = 10.0 if score_val > 0 else -10.0

        # Calculate Lichess Sigmoid formula:
        # P = 1 / (1 + exp(-0.4 * pawns))
        try:
            sigmoid_val = 1.0 / (1.0 + math.exp(-0.4 * pawns))
        except OverflowError:
            sigmoid_val = 1.0 if pawns > 0 else 0.0

        return pawns, sigmoid_val

if __name__ == "__main__":
    sf = StockfishHelper()
    
    # Test equal position
    pawns, sig = sf.analyze_position([], depth=10, active_color='w')
    print(f"Start pos: {pawns:+.2f} pawns, sigmoid: {sig*100:.1f}%")
    
    # Test e4 e5 Nf3
    pawns, sig = sf.analyze_position(["e2e4", "e7e5", "g1f3"], depth=10, active_color='b')
    print(f"e4 e5 Nf3: {pawns:+.2f} pawns, sigmoid: {sig*100:.1f}%")
