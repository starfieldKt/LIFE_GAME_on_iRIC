import numpy as np
import iric
import sys

def update_grid(grid, periodic=True):
    """ライフゲームのルールに基づいてグリッドを更新する関数。
    
    Args:
        grid (np.ndarray): 現在のグリッドの状態。
        periodic (bool): 周期境界条件を使用するかどうか。
    
    Returns:
        np.ndarray: 更新されたグリッドの状態。
    """
    if periodic:
        # 周期境界条件を適用
        left = np.roll(grid, 1, axis=1)
        right = np.roll(grid, -1, axis=1)
        up = np.roll(grid, 1, axis=0)
        down = np.roll(grid, -1, axis=0)
        up_left = np.roll(up, 1, axis=1)
        up_right = np.roll(up, -1, axis=1)
        down_left = np.roll(down, 1, axis=1)
        down_right = np.roll(down, -1, axis=1)
    else:
        # 非周期境界条件を適用
        left = np.zeros_like(grid)
        right = np.zeros_like(grid)
        up = np.zeros_like(grid)
        down = np.zeros_like(grid)
        up_left = np.zeros_like(grid)
        up_right = np.zeros_like(grid)
        down_left = np.zeros_like(grid)
        down_right = np.zeros_like(grid)

        left[:, 1:] = grid[:, :-1]
        right[:, :-1] = grid[:, 1:]
        up[1:, :] = grid[:-1, :]
        down[:-1, :] = grid[1:, :]
        up_left[1:, 1:] = grid[:-1, :-1]
        up_right[1:, :-1] = grid[:-1, 1:]
        down_left[:-1, 1:] = grid[1:, :-1]
        down_right[:-1, :-1] = grid[1:, 1:]

    # 各セルの隣接セル数をカウント
    neighbors = left + right + up + down + up_left + up_right + down_left + down_right

    # ライフゲームのルールを適用
    new_grid = ((neighbors == 3) | ((grid == 1) & (neighbors == 2))).astype(int)
    return new_grid

def open_cgns():
    """CGNSファイルを開く関数。
    
    Returns:
        int: 開いたCGNSファイルのファイルID。
    """
    # コマンドライン引数でCGNSファイル名が指定されているか確認
    if len(sys.argv) < 2:
        print("Error: CGNS file name not specified.")
        exit()

    cgns_name = sys.argv[1]
    print("CGNS file name: " + cgns_name)

    # CGNSファイルを修正モードで開く
    fid = iric.cg_iRIC_Open(cgns_name, iric.IRIC_MODE_MODIFY)
    return fid

def main():
    ###############################################################################
    # CGNSファイルを開く
    ###############################################################################
    fid = open_cgns()

    # 古い計算結果を削除
    iric.cg_iRIC_Clear_Sol(fid)

    ###############################################################################
    # 計算条件を読み込み
    ###############################################################################
    # 計算終了時間を読み込み
    time_end = iric.cg_iRIC_Read_Integer(fid, "time_end")
    # 周期境界条件を読み込み
    if iric.cg_iRIC_Read_Integer(fid, "periodic") == 1:
        periodic = True
    else:
        periodic = False

    # 格子サイズを読み込み
    isize, jsize = iric.cg_iRIC_Read_Grid2d_Str_Size(fid)
    # 初期の生死情報を読み込み
    is_alive = iric.cg_iRIC_Read_Grid_Integer_Cell(fid, "life")
    # 配列の形状がFortran形式の1次元配列なので2次元配列に変換
    is_alive = is_alive.reshape(jsize-1, isize-1).T

    ###############################################################################
    # 初期状態を書き込み
    ###############################################################################
    # 初期の生死情報を書き込み
    iric.cg_iRIC_Write_Sol_Start(fid)
    iric.cg_iRIC_Write_Sol_Time(fid, 0.0)
    iric.cg_iRIC_Write_Sol_Cell_Integer(fid, "life", is_alive.flatten(order='F'))
    iric.cg_iRIC_Write_Sol_End(fid)

    ###############################################################################
    # 時間ループ (1~time_end)
    ###############################################################################
    for t in range(1, time_end + 1):
        # 次の生死情報を計算
        is_alive = update_grid(is_alive, periodic)

        # 次の生死情報を書き込み
        iric.cg_iRIC_Write_Sol_Start(fid)
        iric.cg_iRIC_Write_Sol_Time(fid, float(t))
        iric.cg_iRIC_Write_Sol_Cell_Integer(fid, "life", is_alive.flatten(order='F'))
        iric.cg_iRIC_Write_Sol_End(fid)

        # タイムステップを出力
        print(f"Time step {t} completed.")

        # 生存セル数が0なら終了
        if np.sum(is_alive) == 0:
            print("All cells are dead. Simulation ends.")
            break

        # 計算結果の再読み込みが要求されていれば出力を行う
        iric.cg_iRIC_Check_Update(fid)

        # 計算のキャンセルが押されていればループを抜け出して出力を終了する
        canceled = iric.iRIC_Check_Cancel()
        if canceled == 1:
            print("Cancel button was pressed. Calculation is finishing. . .")
            break
    
    # CGNSファイルをクローズ
    iric.cg_iRIC_Close(fid)

if __name__ == "__main__":
    main()