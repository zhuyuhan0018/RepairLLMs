#!/usr/bin/env python3
"""
下载 patch 文件对应的项目代码（修复前的版本）
用于为模型提供完整的代码库上下文进行分析
"""
import os
import re
import subprocess
import sys
from pathlib import Path


def extract_patch_info(patch_file):
    """从 patch 文件中提取项目信息"""
    with open(patch_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 commit hash
    commit_match = re.search(r'From (\w+)', content)
    if not commit_match:
        raise ValueError("无法从 patch 文件中提取 commit hash")
    
    commit_hash = commit_match.group(1)
    
    # 根据代码特征判断项目
    project_info = {
        'open62541': {
            'repo': 'https://github.com/open62541/open62541.git',
            'indicators': ['UA_Session', 'UA_Server', 'OPC UA', 'open62541']
        },
        'harfbuzz': {
            'repo': 'https://github.com/harfbuzz/harfbuzz.git',
            'indicators': ['hb_', 'HarfBuzz']
        }
    }
    
    detected_project = None
    for project, info in project_info.items():
        if any(indicator in content for indicator in info['indicators']):
            detected_project = project
            repo_url = info['repo']
            break
    
    if not detected_project:
        # 默认尝试 open62541（因为当前 patch 是 open62541）
        detected_project = 'open62541'
        repo_url = project_info['open62541']['repo']
        print(f"警告: 无法确定项目，默认使用 {detected_project}")
    
    return {
        'project': detected_project,
        'repo_url': repo_url,
        'commit_hash': commit_hash
    }


def download_codebase(patch_file, output_dir=None):
    """
    下载 patch 对应的代码库（修复前的版本）
    
    Args:
        patch_file: patch 文件路径
        output_dir: 输出目录，默认为 datasets/codebases/{project}/
    """
    patch_path = Path(patch_file)
    if not patch_path.exists():
        raise FileNotFoundError(f"Patch 文件不存在: {patch_file}")
    
    print(f"分析 patch 文件: {patch_file}")
    info = extract_patch_info(patch_file)
    
    print(f"\n项目信息:")
    print(f"  项目名称: {info['project']}")
    print(f"  仓库地址: {info['repo_url']}")
    print(f"  Commit Hash: {info['commit_hash']}")
    
    # 确定输出目录
    if output_dir is None:
        output_dir = Path(f"datasets/codebases/{info['project']}")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果目录已存在且是 git 仓库，先检查是否需要更新
    if (output_dir / '.git').exists():
        print(f"\n检测到已存在的代码库: {output_dir}")
        response = input("是否重新克隆？(y/N): ").strip().lower()
        if response == 'y':
            print(f"删除现有目录: {output_dir}")
            import shutil
            shutil.rmtree(output_dir)
        else:
            print("使用现有代码库")
            # 切换到指定 commit 的父 commit
            print(f"\n切换到修复前的版本...")
            subprocess.run(['git', 'fetch', 'origin'], cwd=output_dir, check=False)
            # 获取父 commit
            result = subprocess.run(
                ['git', 'rev-parse', f'{info["commit_hash"]}^'],
                cwd=output_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                parent_commit = result.stdout.strip()
                print(f"父 commit (修复前): {parent_commit}")
                subprocess.run(['git', 'checkout', parent_commit], cwd=output_dir, check=True)
                print("✓ 已切换到修复前的版本")
            else:
                print("警告: 无法获取父 commit，尝试直接 checkout")
                subprocess.run(['git', 'checkout', info['commit_hash']], cwd=output_dir, check=False)
            return str(output_dir)
    
    # 克隆仓库
    print(f"\n克隆仓库到: {output_dir}")
    subprocess.run(
        ['git', 'clone', info['repo_url'], str(output_dir)],
        check=True
    )
    
    # 切换到修复前的版本（父 commit）
    print(f"\n切换到修复前的版本...")
    result = subprocess.run(
        ['git', 'rev-parse', f'{info["commit_hash"]}^'],
        cwd=output_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        parent_commit = result.stdout.strip()
        print(f"父 commit (修复前): {parent_commit}")
        subprocess.run(['git', 'checkout', parent_commit], cwd=output_dir, check=True)
        print("✓ 已切换到修复前的版本")
    else:
        # 如果无法获取父 commit，直接 checkout 到指定 commit
        print(f"警告: 无法获取父 commit，切换到 commit {info['commit_hash']}")
        subprocess.run(['git', 'checkout', info['commit_hash']], cwd=output_dir, check=True)
    
    print(f"\n✓ 代码库下载完成: {output_dir}")
    return str(output_dir)


def main():
    if len(sys.argv) < 2:
        print("用法: python download_codebase.py <patch_file> [output_dir]")
        print("\n示例:")
        print("  python download_codebase.py datasets/testdata/patches/use_after_free/42470745.patch")
        print("  python download_codebase.py datasets/testdata/patches/use_after_free/42470745.patch datasets/codebases/open62541")
        sys.exit(1)
    
    patch_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        codebase_path = download_codebase(patch_file, output_dir)
        print(f"\n代码库路径: {codebase_path}")
        print("\n现在可以在 RepairPipeline 中使用此路径作为 codebase_path 参数")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

