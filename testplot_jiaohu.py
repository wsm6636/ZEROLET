import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import ast
import sys
import os

def plot_interactive_heatmap(file_path):
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    # 2. 读取数据
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"读取文件出错: {e}")
        return

    # 3. 数据清洗：提取 LF (针对你提供的不同 CSV 格式做适配)
    try:
        if 'max_diff_sync_LF' in df.columns:
            df['LF_val'] = df['max_diff_sync_LF']
        # if 'min_diff_sync_LF' in df.columns:
            # df['LF_val'] = df['min_diff_sync_LF']
        elif 'diff_sync' in df.columns:
            # 解析字符串列表并取第一个元素
            df['LF_val'] = df['diff_sync'].apply(lambda x: ast.literal_eval(x)[0])
        else:
            df['LF_val'] = df['LF'] # 备用名
    except Exception as e:
        print(f"解析 LF 数值失败: {e}")
        return

    # 4. 创建透视表 (保持组合不拆开)

    if 'max_diff_sync_LF' in df.columns:
        pivot_table = df.pivot_table(index='max_offset_LF_read', 
                                 columns='max_offset_LF_write', 
                                 values='LF_val', 
                                 aggfunc='max')
    # if 'min_diff_sync_LF' in df.columns:
    #     pivot_table = df.pivot_table(index='min_offset_LF_read', 
    #                              columns='min_offset_LF_write', 
    #                              values='LF_val', 
    #                              aggfunc='max')
    else:
        pivot_table = df.pivot_table(index='read_offsets', 
                                 columns='write_offsets', 
                                 values='LF_val', 
                                 aggfunc='max')

    # 5. 构造 Plotly 交互式热力图
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns, # Write Offsets
        y=pivot_table.index,   # Read Offsets
        colorscale='YlOrRd',
        # 自定义悬停显示内容：完美解决坐标对应难题
        hovertemplate=(
            "<b>Read Combo:</b> %{y}<br>" +
            "<b>Write Combo:</b> %{x}<br>" +
            "<b>LF Value:</b> %{z}<br>" +
            "<extra></extra>" # 隐藏右侧多余的 trace 标记
        )
    ))

    # 6. 优化布局
    fig.update_layout(
        title=f'Interactive DiffLF Heatmap<br>Source: {os.path.basename(file_path)}',
        xaxis_title="Write Offset Combination [W1, W2, W3]",
        yaxis_title="Read Offset Combination [R1, R2, R3]",
        xaxis={'tickangle': 45},
        # 增加高度和宽度以容纳大量数据
        height=900,
        width=1100
    )

    # 7. 离线保存并自动打开
    output_name = "interactive_difflf_heatmap.html"
    # include_plotlyjs='all' 确保在无网络环境下也能用 Chrome 打开
    pio.write_html(fig, file=output_name, include_plotlyjs='all', auto_open=True)
    
    print(f"成功！交互式热力图已生成: {output_name}")
    print("提示：在浏览器中将鼠标悬停在格子处即可查看精确坐标。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python interactive_plot.py <your_data.csv>")
    else:
        plot_interactive_heatmap(sys.argv[1])