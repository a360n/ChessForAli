import os
from video_engine import VideoEngine

def main():
    print("==================================================")
    # Chess2Video Native System Verification
    print("==================================================")
    
    ve = VideoEngine()
    os.makedirs("./output_tests", exist_ok=True)
    
    # Morphy's famous Opera Game PGN
    opera_game_pgn = """[Event "A Night at the Opera"]
[Site "Paris FRA"]
[Date "1858.11.02"]
[Round "1"]
[White "Morphy, Paul"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0"""

    def progress_callback(msg, pct):
        print(f"[{pct}%] {msg}")

    # 1. Test YouTube Landscape (16:9)
    print("\n[TEST 1] Compiling Opera Game in 16:9 Landscape...")
    output_169 = "./output_tests/opera_game_169.mp4"
    try:
        ve.generate_chess_video(
            pgn_text=opera_game_pgn,
            output_path=output_169,
            board_theme="wood",
            piece_theme="cburnett",
            aspect_ratio="16:9",
            hold_duration=0.8,
            volume=4.0,
            progress_callback=progress_callback
        )
        size = os.path.getsize(output_169)
        print(f"Success! 16:9 Video created at: {output_169} ({size} bytes)")
    except Exception as e:
        print(f"16:9 Video compilation failed: {e}")

    # 2. Test TikTok/Shorts Portrait (9:16)
    print("\n[TEST 2] Compiling Opera Game in 9:16 Portrait...")
    output_916 = "./output_tests/opera_game_916.mp4"
    try:
        ve.generate_chess_video(
            pgn_text=opera_game_pgn,
            output_path=output_916,
            board_theme="blue",
            piece_theme="cburnett",
            aspect_ratio="9:16",
            hold_duration=0.6,
            volume=8.0,
            progress_callback=progress_callback
        )
        size = os.path.getsize(output_916)
        print(f"Success! 9:16 Video created at: {output_916} ({size} bytes)")
    except Exception as e:
        print(f"9:16 Video compilation failed: {e}")

    print("\n==================================================")
    print("Verification Completed!")
    print("==================================================")

if __name__ == "__main__":
    main()
