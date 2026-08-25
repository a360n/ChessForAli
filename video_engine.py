import os
import subprocess
import math
from PIL import Image, ImageDraw, ImageFont
from chess_logic import Board
from stockfish_helper import StockfishHelper

class VideoEngine:
    def __init__(self):
        self.sf = StockfishHelper()

    def convert_svgs_to_pngs(self, theme_name, size=128):
        """Converts all SVG pieces of the given theme to PNGs using native macOS sips"""
        src_dir = os.path.abspath(f"./assets/pieces/{theme_name}")
        dest_dir = os.path.abspath(f"./assets/pieces_png/{theme_name}_{size}")
        
        if os.path.exists(dest_dir):
            # Already exists, verify we have 12 files
            if len([f for f in os.listdir(dest_dir) if f.endswith('.png')]) == 12:
                return dest_dir
                
        os.makedirs(dest_dir, exist_ok=True)
        pieces = ["bB", "bK", "bN", "bP", "bQ", "bR", "wB", "wK", "wN", "wP", "wQ", "wR"]
        for p in pieces:
            svg_path = os.path.join(src_dir, f"{p}.svg")
            png_path = os.path.join(dest_dir, f"{p}.png")
            
            # Call sips to convert: sips -z size size -s format png svg_path --out png_path
            cmd = ["sips", "-z", str(size), str(size), "-s", "format", "png", svg_path, "--out", png_path]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as e:
                print(f"Error converting piece {p}: {e}")
                
        return dest_dir

    def draw_rounded_rect(self, draw, coords, radius, color):
        """Draws a rounded rectangle"""
        draw.rounded_rectangle(coords, radius, fill=color)

    def generate_chess_video(self, pgn_text, output_path, board_theme="green", piece_theme="cburnett", aspect_ratio="16:9", hold_duration=0.8, volume=1.0, progress_callback=None):
        """Generates the MP4 video with smooth sliding animations, eval bar, and audio synced moves"""
        if progress_callback:
            progress_callback("Parsing PGN game and converting moves...", 5)

        # 1. Parse PGN and get move sequence
        board = Board()
        raw_moves = board.parse_pgn_moves(pgn_text)
        
        # Translate SAN to UCI moves
        uci_moves = []
        board.reset()
        for idx, san in enumerate(raw_moves):
            try:
                uci = board.parse_san(san)
                uci_moves.append(uci)
                board.make_move(uci)
            except Exception as e:
                raise ValueError(f"Move {idx+1} ({san}) parsing failed: {e}")

        total_moves = len(uci_moves)
        if total_moves == 0:
            raise ValueError("The PGN does not contain any valid moves!")

        if progress_callback:
            progress_callback(f"Running Stockfish analysis on {total_moves} moves...", 10)

        # 2. Run Stockfish to get FEN states and evaluations
        # We need the state *before* the first move (starting pos) and *after* each move
        states = []
        
        # Start state
        board.reset()
        eval_pawns, eval_sig = self.sf.analyze_position([], depth=10, active_color='w')
        states.append({
            'fen': board.to_fen(),
            'eval_pawns': eval_pawns,
            'eval_sig': eval_sig,
            'check_sq': None,
            'last_move': None
        })

        for idx, uci in enumerate(uci_moves):
            if progress_callback:
                progress_callback(f"Analyzing move {idx+1}/{total_moves} using Stockfish...", 10 + int(40 * (idx+1)/total_moves))
            
            # Make move
            board.make_move(uci)
            active_color = board.turn
            
            # Analyze
            eval_pawns, eval_sig = self.sf.analyze_position(uci_moves[:idx+1], depth=10, active_color=active_color)
            
            # Check if king is in check
            # We look at the board grid to find king of the active color
            king_char = 'K' if active_color == 'w' else 'k'
            king_sq = None
            for r in range(8):
                for c in range(8):
                    pc = board.grid[r][c]
                    if pc and pc[0] == active_color and pc[1] == 'K':
                        king_sq = board.coords_to_sq(c, r)
                        break
            
            # Is in check? We check if any enemy piece attacks the king square
            # For simplicity, we check if the king is in check using a dummy calculation
            # If active color is w, we toggle turn to b to see if white king is under attack
            # But wait, Stockfish output itself has "Checkers: " line! E.g. "Checkers: a4"
            # Since our subprocess runner from earlier got Checkers from Stockfish 'd' command:
            # Let's see: we can query Stockfish for blockers/checkers or write a simple check detector.
            # In our Board class, we can determine check by checking if any enemy piece can legally move to king square!
            is_check = False
            if king_sq:
                king_c, king_r = board.sq_to_coords(king_sq)
                enemy_color = 'b' if active_color == 'w' else 'w'
                for r in range(8):
                    for c in range(8):
                        pc = board.grid[r][c]
                        if pc and pc[0] == enemy_color:
                            # If an enemy piece can attack king_sq
                            if (king_c, king_r) in board.get_pseudo_legal_moves(c, r):
                                is_check = True
                                break

            states.append({
                'fen': board.to_fen(),
                'eval_pawns': eval_pawns,
                'eval_sig': eval_sig,
                'check_sq': king_sq if is_check else None,
                'last_move': uci
            })

        # 3. Setup Layout & Dimensions
        if aspect_ratio == "16:9":
            width, height = 1280, 720
            sq_size = 64
            board_w = board_h = 8 * sq_size # 512
            board_x = (width - board_w) // 2 + 50 # 434
            board_y = (height - board_h) // 2 # 104
            eval_w, eval_h = 20, board_h
            eval_x = board_x - 36
            eval_y = board_y
            player_black_pos = (board_x, board_y - 34)
            player_white_pos = (board_x, board_y + board_h + 10)
        else: # 9:16
            width, height = 720, 1280
            sq_size = 80
            board_w = board_h = 8 * sq_size # 640
            board_x = 50
            board_y = (height - board_h) // 2 # 320
            eval_w, eval_h = 24, board_h
            eval_x = 16
            eval_y = board_y
            player_black_pos = (board_x, board_y - 45)
            player_white_pos = (board_x, board_y + board_h + 15)

        # Pre-render piece SVGs to PNGs using sips
        if progress_callback:
            progress_callback("Converting SVG chess pieces to PNGs...", 55)
        pieces_dir = self.convert_svgs_to_pngs(piece_theme, sq_size)

        # Cache PNG piece images in Pillow
        piece_imgs = {}
        for p in ["bB", "bK", "bN", "bP", "bQ", "bR", "wB", "wK", "wN", "wP", "wQ", "wR"]:
            piece_imgs[p] = Image.open(os.path.join(pieces_dir, f"{p}.png")).convert("RGBA")

        # Define Colors
        themes = {
            "green": {
                "light": (238, 238, 210),
                "dark": (118, 150, 86),
                "bg_start": (18, 18, 20),
                "bg_end": (30, 30, 36),
                "highlight_last": (247, 247, 105, 120),
                "highlight_check": (235, 64, 52, 140)
            },
            "wood": {
                "light": (240, 217, 181),
                "dark": (181, 136, 99),
                "bg_start": (15, 13, 12),
                "bg_end": (29, 24, 21),
                "highlight_last": (218, 196, 50, 120),
                "highlight_check": (220, 50, 50, 140)
            },
            "blue": {
                "light": (226, 228, 230),
                "dark": (59, 104, 140),
                "bg_start": (10, 15, 29),
                "bg_end": (20, 27, 48),
                "highlight_last": (220, 220, 80, 120),
                "highlight_check": (240, 60, 60, 140)
            }
        }
        theme = themes.get(board_theme, themes["green"])

        # Determine output temp video path
        temp_video_path = output_path.replace(".mp4", "_temp.mp4")
        
        # Initialize FFmpeg raw video compiler pipe
        ffmpeg_cmd = [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", "30",
            "-i", "-",
            "-an",
            "-vcodec", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            temp_video_path
        ]
        
        if progress_callback:
            progress_callback("Launching FFmpeg video compiler...", 60)
            
        try:
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch FFmpeg: {e}")

        # Draw helper functions
        def draw_gradient_background(draw):
            # Vertical gradient
            for y in range(height):
                t = y / height
                r = int(theme["bg_start"][0] * (1 - t) + theme["bg_end"][0] * t)
                g = int(theme["bg_start"][1] * (1 - t) + theme["bg_end"][1] * t)
                b = int(theme["bg_start"][2] * (1 - t) + theme["bg_end"][2] * t)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

        def draw_board_squares(draw, last_move=None, check_sq=None):
            # Draw squares
            for r in range(8):
                for c in range(8):
                    x = board_x + c * sq_size
                    y = board_y + (7 - r) * sq_size
                    color = theme["light"] if (r + c) % 2 != 0 else theme["dark"]
                    draw.rectangle([x, y, x + sq_size, y + sq_size], fill=color)

            # Highlight last move
            if last_move:
                src_sq, dest_sq = last_move[:2], last_move[2:4]
                for sq in [src_sq, dest_sq]:
                    c, r = Board.sq_to_coords(sq)
                    x = board_x + c * sq_size
                    y = board_y + (7 - r) * sq_size
                    
                    # Blend highlight
                    highlight_img = Image.new("RGBA", (sq_size, sq_size), theme["highlight_last"])
                    im.alpha_composite(highlight_img, (x, y))

            # Highlight check
            if check_sq:
                c, r = Board.sq_to_coords(check_sq)
                x = board_x + c * sq_size
                y = board_y + (7 - r) * sq_size
                highlight_img = Image.new("RGBA", (sq_size, sq_size), theme["highlight_check"])
                im.alpha_composite(highlight_img, (x, y))

        def draw_eval_bar(draw, level):
            """Draws the dynamic evaluation bar. Level in [0, 1] represents White advantage"""
            # Draw black background
            draw.rectangle([eval_x, eval_y, eval_x + eval_w, eval_y + eval_h], fill=(30, 30, 30))
            
            # White bar height based on level
            # 0.0 -> White has 0% (fully Black bar)
            # 1.0 -> White has 100% (fully White bar)
            white_bar_h = int(level * eval_h)
            
            # White fills from bottom (chess standard: white is on bottom of board)
            if white_bar_h > 0:
                draw.rectangle([eval_x, eval_y + eval_h - white_bar_h, eval_x + eval_w, eval_y + eval_h], fill=(240, 240, 240))
                
            # Draw center equilibrium marker line
            draw.line([(eval_x, eval_y + eval_h // 2), (eval_x + eval_w, eval_y + eval_h // 2)], fill=(120, 120, 120), width=1)

        def draw_player_tags(draw):
            # Load font or fall back
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except:
                font = font_small = ImageFont.load_default()
                
            # Black Player
            draw.text((player_black_pos[0], player_black_pos[1]), "Black Player", fill=(180, 180, 180), font=font)
            # White Player
            draw.text((player_white_pos[0], player_white_pos[1]), "White Player", fill=(240, 240, 240), font=font)

        # 4. Rendering Frame Loop
        # Move timings
        fps = 30
        slide_frames = 6 # 0.2s duration
        hold_frames = int(hold_duration * fps) # e.g. 24 frames for 0.8s hold
        
        # Calculate total frames
        # Start position holds for 1s (30 frames)
        # Each move has slide_frames + hold_frames
        # End position holds for 2s (60 frames)
        start_hold_frames = 30
        end_hold_frames = 60
        total_frames = start_hold_frames + total_moves * (slide_frames + hold_frames) + end_hold_frames
        
        frame_idx = 0

        # Draw Start Position hold frames
        for _ in range(start_hold_frames):
            im = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(im)
            draw_gradient_background(draw)
            draw_board_squares(draw)
            draw_eval_bar(draw, states[0]['eval_sig'])
            draw_player_tags(draw)

            # Draw static pieces
            start_board = Board()
            start_board.load_fen(states[0]['fen'])
            for r in range(8):
                for c in range(8):
                    pc = start_board.grid[r][c]
                    if pc:
                        pc_str = pc[0] + pc[1]
                        x = board_x + c * sq_size
                        y = board_y + (7 - r) * sq_size
                        im.alpha_composite(piece_imgs[pc_str], (x, y))

            # Send to FFmpeg
            ffmpeg_process.stdin.write(im.convert("RGB").tobytes())
            frame_idx += 1

        # For mapping sounds
        # Audio events will store (timestamp_seconds, sound_type)
        audio_events = []

        # Draw Moves
        for move_num in range(total_moves):
            uci = uci_moves[move_num]
            prev_state = states[move_num]
            curr_state = states[move_num + 1]

            src_sq, dest_sq = uci[:2], uci[2:4]
            src_c, src_r = Board.sq_to_coords(src_sq)
            dest_c, dest_r = Board.sq_to_coords(dest_sq)

            # Check sound type
            # Standard move is default. If capture is involved, play capture. If castling, play castling. If check, play check.
            board_before = Board()
            board_before.load_fen(prev_state['fen'])
            
            is_capture = board_before.grid[dest_r][dest_c] is not None or (board_before.grid[src_r][src_c] and board_before.grid[src_r][src_c][1] == 'P' and dest_sq == board_before.ep_square)
            is_castling = board_before.grid[src_r][src_c] and board_before.grid[src_r][src_c][1] == 'K' and abs(dest_c - src_c) == 2
            is_check = curr_state['check_sq'] is not None

            sound_type = "move"
            if is_check:
                sound_type = "check"
            elif is_castling:
                sound_type = "castling"
            elif is_capture:
                sound_type = "capture"

            # Add audio event timestamp
            sound_time = (start_hold_frames + move_num * (slide_frames + hold_frames)) / fps
            audio_events.append((sound_time, sound_type))

            # A. Draw sliding animation frames (slide_frames = 6)
            for f in range(slide_frames):
                if progress_callback:
                    progress_callback(f"Rendering frame {frame_idx}/{total_frames}...", 60 + int(30 * frame_idx/total_frames))

                im = Image.new("RGBA", (width, height))
                draw = ImageDraw.Draw(im)
                draw_gradient_background(draw)
                
                # Board squares (highlight last move only on current frame destination)
                draw_board_squares(draw, last_move=uci)
                
                # Interpolate evaluation bar level
                t_slide = f / (slide_frames - 1.0) if slide_frames > 1 else 1.0
                curr_eval = prev_state['eval_sig'] + t_slide * (curr_state['eval_sig'] - prev_state['eval_sig'])
                draw_eval_bar(draw, curr_eval)
                draw_player_tags(draw)

                # Draw static and sliding pieces
                # Setup board at starting state of this ply
                temp_board = Board()
                temp_board.load_fen(prev_state['fen'])
                
                # Draw pieces except the moving ones
                for r in range(8):
                    for c in range(8):
                        if (c == src_c and r == src_r):
                            continue
                        # If castling, skip the rook as well as it will slide too
                        if is_castling:
                            rook_r = src_r
                            rook_src_c = 7 if dest_c == 6 else 0
                            if c == rook_src_c and r == rook_r:
                                continue
                        
                        pc = temp_board.grid[r][c]
                        if pc:
                            pc_str = pc[0] + pc[1]
                            x = board_x + c * sq_size
                            y = board_y + (7 - r) * sq_size
                            im.alpha_composite(piece_imgs[pc_str], (x, y))

                # Now draw the sliding piece(s)
                # Primary piece sliding (King or other piece)
                slide_c = src_c + t_slide * (dest_c - src_c)
                slide_r = src_r + t_slide * (dest_r - src_r)
                
                moving_piece = temp_board.grid[src_r][src_c]
                if moving_piece:
                    pc_str = moving_piece[0] + moving_piece[1]
                    # Convert grid slide coordinates to canvas coordinates
                    x = board_x + slide_c * sq_size
                    y = board_y + (7 - slide_r) * sq_size
                    im.alpha_composite(piece_imgs[pc_str], (int(x), int(y)))

                # Secondary piece sliding (Rook if castling)
                if is_castling:
                    rook_r = src_r
                    rook_src_c = 7 if dest_c == 6 else 0
                    rook_dest_c = 5 if dest_c == 6 else 3
                    
                    rook_slide_c = rook_src_c + t_slide * (rook_dest_c - rook_src_c)
                    
                    rook_piece = temp_board.grid[rook_r][rook_src_c]
                    if rook_piece:
                        pc_str = rook_piece[0] + rook_piece[1]
                        x = board_x + rook_slide_c * sq_size
                        y = board_y + (7 - rook_r) * sq_size
                        im.alpha_composite(piece_imgs[pc_str], (int(x), int(y)))

                # Send frame to FFmpeg
                ffmpeg_process.stdin.write(im.convert("RGB").tobytes())
                frame_idx += 1

            # B. Draw static hold frames (hold_frames = 24)
            for f in range(hold_frames):
                if progress_callback:
                    progress_callback(f"Rendering frame {frame_idx}/{total_frames}...", 60 + int(30 * frame_idx/total_frames))

                im = Image.new("RGBA", (width, height))
                draw = ImageDraw.Draw(im)
                draw_gradient_background(draw)
                
                # Board squares with highlights
                draw_board_squares(draw, last_move=uci, check_sq=curr_state['check_sq'])
                draw_eval_bar(draw, curr_state['eval_sig'])
                draw_player_tags(draw)

                # Draw static pieces of current position
                curr_board = Board()
                curr_board.load_fen(curr_state['fen'])
                for r in range(8):
                    for c in range(8):
                        pc = curr_board.grid[r][c]
                        if pc:
                            pc_str = pc[0] + pc[1]
                            x = board_x + c * sq_size
                            y = board_y + (7 - r) * sq_size
                            im.alpha_composite(piece_imgs[pc_str], (x, y))

                # Send frame to FFmpeg
                ffmpeg_process.stdin.write(im.convert("RGB").tobytes())
                frame_idx += 1

        # Draw End Position hold frames (2 seconds = 60 frames)
        last_state = states[-1]
        for _ in range(end_hold_frames):
            if progress_callback:
                progress_callback(f"Rendering frame {frame_idx}/{total_frames}...", 60 + int(30 * frame_idx/total_frames))

            im = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(im)
            draw_gradient_background(draw)
            draw_board_squares(draw, last_move=last_state['last_move'], check_sq=last_state['check_sq'])
            draw_eval_bar(draw, last_state['eval_sig'])
            draw_player_tags(draw)

            # Draw static pieces
            end_board = Board()
            end_board.load_fen(last_state['fen'])
            for r in range(8):
                for c in range(8):
                    pc = end_board.grid[r][c]
                    if pc:
                        pc_str = pc[0] + pc[1]
                        x = board_x + c * sq_size
                        y = board_y + (7 - r) * sq_size
                        im.alpha_composite(piece_imgs[pc_str], (x, y))

            # Send to FFmpeg
            ffmpeg_process.stdin.write(im.convert("RGB").tobytes())
            frame_idx += 1

        # Terminate FFmpeg compiler process
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()

        # 5. Audio Mix & Muxing Pass
        if progress_callback:
            progress_callback("Mixing chess sound effects and final encoding...", 92)

        # Mapping sound types to files in assets/sounds/standard/
        sound_files = {
            "move": os.path.abspath("./assets/sounds/standard/Move.mp3"),
            "capture": os.path.abspath("./assets/sounds/standard/Capture.mp3"),
            "castling": os.path.abspath("./assets/sounds/standard/Confirmation.mp3"),
            "check": os.path.abspath("./assets/sounds/standard/Capture.mp3") # Fall back if check.mp3 is 14 bytes
        }
        
        # Verify check file size
        check_path = os.path.abspath("./assets/sounds/standard/Check.mp3")
        if os.path.exists(check_path) and os.path.getsize(check_path) > 100:
            sound_files["check"] = check_path

        # Construct FFmpeg complex filter command for audio delays and mixing
        # Command syntax:
        # ffmpeg -y -i temp_video.mp4 -i sound1.mp3 -i sound2.mp3 -filter_complex "[1:a]adelay=delay1|delay1[a1]; [2:a]adelay=delay2|delay2[a2]; [0:a][a1][a2]amix=inputs=3:duration=first" -map 0:v -map "[a]" output.mp4
        # Wait, since the temp video has NO audio stream, we cannot map [0:a]! We need a silent audio background source!
        # FFmpeg has a built-in virtual audio source: anullsrc!
        # `anullsrc=r=44100:cl=stereo`
        # Let's add that to filter_complex as the base audio channel, or just use amix on delayed tracks!
        # If we use amix on delayed tracks, we don't need a silent track as long as we map the output, but amix might fail if inputs=0.
        # Actually, adding a silent background is extremely robust!
        # Filter complex:
        # `[0:a]anullsrc=channel_layout=stereo:sample_rate=44100[silent]; [1:a]adelay=delay1|delay1[a1]; [silent][a1]amix=inputs=2:duration=first[out]`
        # Or even simpler: we can use a virtual input: `-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100`!
        # This is incredibly clean!
        
        audio_inputs = []
        filter_parts = []
        mix_inputs = []
        
        # Virtual input 0: temp video
        # Virtual input 1: silent audio source
        ffmpeg_audio_cmd = [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-i", temp_video_path,
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"
        ]
        
        # Add audio event inputs
        # Keep track of sound files mapped to inputs to avoid overloading if many identical inputs
        # But wait! Having separate inputs for each event is fine, as each gets delayed differently.
        # So we just add each event's sound file as a separate input.
        # Inputs will be indexed from 2 onwards:
        # 0: video
        # 1: silence (virtual)
        # 2, 3, 4...: sound clips
        
        for idx, (t, stype) in enumerate(audio_events):
            sfile = sound_files.get(stype, sound_files["move"])
            ffmpeg_audio_cmd.extend(["-i", sfile])
            
            # Delay in ms
            delay_ms = int(t * 1000)
            input_idx = 2 + idx
            
            filter_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{input_idx}]")
            mix_inputs.append(f"[a{input_idx}]")

        # Compile filter complex
        # Combine silence (input 1) with all delayed inputs
        mix_inputs_str = "".join(mix_inputs)
        total_mix_inputs = len(mix_inputs) + 1 # include silence
        
        # Limit total inputs to mix
        # If no moves: just mix silence
        if total_mix_inputs == 1:
            filter_complex = f"anullsrc=channel_layout=stereo:sample_rate=44100,volume={volume},alimiter[aout]"
        else:
            filter_complex = "; ".join(filter_parts) + f"; [1:a]{mix_inputs_str}amix=inputs={total_mix_inputs}:duration=first:dropout_transition=0:normalize=0,volume={volume},alimiter[aout]"

        ffmpeg_audio_cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy", # Copy video directly (ultra fast, no re-encoding!)
            "-c:a", "aac",
            "-shortest",
            output_path
        ])

        try:
            subprocess.run(ffmpeg_audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            raise RuntimeError(f"FFmpeg audio mixing failed: {e}")
        finally:
            # Clean up temp video file
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        if progress_callback:
            progress_callback("Chess2Video generation complete!", 100)

        return output_path

if __name__ == "__main__":
    # Test generation with an extremely simple PGN
    ve = VideoEngine()
    test_pgn = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5"
    os.makedirs("./output_tests", exist_ok=True)
    
    def log_progress(msg, pct):
        print(f"[{pct}%] {msg}")

    print("Starting test video generation...")
    ve.generate_chess_video(
        test_pgn, 
        "./output_tests/test_game.mp4", 
        board_theme="green", 
        piece_theme="cburnett", 
        aspect_ratio="16:9", 
        hold_duration=0.8,
        volume=1.0,
        progress_callback=log_progress
    )
    print("Test video generated successfully at ./output_tests/test_game.mp4!")
