#!/bin/bash

# 实验运行脚本
# 用于执行各种语义还原实验

# 设置环境变量
export PYTHONPATH="$(pwd)/.."

# 建模文件路径
MODELING_FILE="../annotated-benchmark.report"
OUTPUT_DIR="./results"
MODEL="gpt-4-turbo"  # 默认模型

# 创建输出目录
mkdir -p $OUTPUT_DIR

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印帮助信息
function print_help {
  echo -e "${YELLOW}语义还原实验运行脚本${NC}"
  echo "用法: $0 [选项] [命令]"
  echo ""
  echo "命令:"
  echo "  di            运行依赖注入还原实验"
  echo "  aop           运行AOP切面还原实验"
  echo "  complete      运行完整代码还原实验"
  echo "  compare       运行模型对比实验"
  echo "  batch         批量运行实验"
  echo "  all           运行所有实验"
  echo ""
  echo "选项:"
  echo "  -h, --help    显示此帮助信息"
  echo "  -m, --model   指定LLM模型 (默认: gpt-4-turbo)"
  echo "  -o, --output  指定输出目录 (默认: ./results)"
  echo ""
  echo "示例:"
  echo "  $0 di --class CommandInjectionController"
  echo "  $0 --model claude-3-opus batch complete"
}

# 参数解析
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -h|--help)
      print_help
      exit 0
      ;;
    -m|--model)
      MODEL="$2"
      shift
      shift
      ;;
    -o|--output)
      OUTPUT_DIR="$2"
      shift
      shift
      ;;
    -c|--class)
      CLASS_NAME="$2"
      shift
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

# 验证命令行参数
if [ $# -eq 0 ]; then
  echo -e "${RED}错误: 未指定命令${NC}"
  print_help
  exit 1
fi

COMMAND=$1
shift

# 运行依赖注入实验
function run_di_experiment {
  if [ -z "$CLASS_NAME" ]; then
    echo -e "${RED}错误: 未指定类名${NC}"
    exit 1
  fi
  
  # 根据类名确定源文件路径
  SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/${CLASS_NAME}.java"
  if [ ! -f "$SOURCE_FILE" ]; then
    # 尝试在 aspect 目录中查找
    SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/aspect/${CLASS_NAME}.java"
    if [ ! -f "$SOURCE_FILE" ]; then
      # 尝试在 service 目录中查找
      SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/service/${CLASS_NAME}.java"
      if [ ! -f "$SOURCE_FILE" ]; then
        echo -e "${RED}错误: 找不到类 ${CLASS_NAME} 的源文件${NC}"
        exit 1
      fi
    fi
  fi
  
  echo -e "${GREEN}运行依赖注入还原实验: ${CLASS_NAME}${NC}"
  python3 experiment_runner.py --modeling-file $MODELING_FILE --output-dir $OUTPUT_DIR --model $MODEL di --class-name $CLASS_NAME --source-file $SOURCE_FILE
}

# 运行AOP实验
function run_aop_experiment {
  if [ -z "$CLASS_NAME" ]; then
    echo -e "${RED}错误: 未指定类名${NC}"
    exit 1
  fi
  
  # 根据类名确定源文件路径
  SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/${CLASS_NAME}.java"
  if [ ! -f "$SOURCE_FILE" ]; then
    # 尝试在 aspect 目录中查找
    SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/aspect/${CLASS_NAME}.java"
    if [ ! -f "$SOURCE_FILE" ]; then
      # 尝试在 service 目录中查找
      SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/service/${CLASS_NAME}.java"
      if [ ! -f "$SOURCE_FILE" ]; then
        echo -e "${RED}错误: 找不到类 ${CLASS_NAME} 的源文件${NC}"
        exit 1
      fi
    fi
  fi
  
  echo -e "${GREEN}运行AOP切面还原实验: ${CLASS_NAME}${NC}"
  python3 experiment_runner.py --modeling-file $MODELING_FILE --output-dir $OUTPUT_DIR --model $MODEL aop --class-name $CLASS_NAME --source-file $SOURCE_FILE
}

# 运行完整代码还原实验
function run_complete_experiment {
  if [ -z "$CLASS_NAME" ]; then
    echo -e "${RED}错误: 未指定类名${NC}"
    exit 1
  fi
  
  # 根据类名确定源文件路径
  SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/${CLASS_NAME}.java"
  if [ ! -f "$SOURCE_FILE" ]; then
    # 尝试在 aspect 目录中查找
    SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/aspect/${CLASS_NAME}.java"
    if [ ! -f "$SOURCE_FILE" ]; then
      # 尝试在 service 目录中查找
      SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/service/${CLASS_NAME}.java"
      if [ ! -f "$SOURCE_FILE" ]; then
        echo -e "${RED}错误: 找不到类 ${CLASS_NAME} 的源文件${NC}"
        exit 1
      fi
    fi
  fi
  
  echo -e "${GREEN}运行完整代码还原实验: ${CLASS_NAME}${NC}"
  python3 experiment_runner.py --modeling-file $MODELING_FILE --output-dir $OUTPUT_DIR --model $MODEL complete --class-name $CLASS_NAME --source-file $SOURCE_FILE
}

# 运行模型对比实验
function run_compare_experiment {
  if [ -z "$CLASS_NAME" ]; then
    echo -e "${RED}错误: 未指定类名${NC}"
    exit 1
  fi
  
  # 根据类名确定源文件路径
  SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/${CLASS_NAME}.java"
  if [ ! -f "$SOURCE_FILE" ]; then
    # 尝试在 aspect 目录中查找
    SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/aspect/${CLASS_NAME}.java"
    if [ ! -f "$SOURCE_FILE" ]; then
      # 尝试在 service 目录中查找
      SOURCE_FILE="../benchmark/src/main/java/edu/thu/benchmark/annotated/service/${CLASS_NAME}.java"
      if [ ! -f "$SOURCE_FILE" ]; then
        echo -e "${RED}错误: 找不到类 ${CLASS_NAME} 的源文件${NC}"
        exit 1
      fi
    fi
  fi
  
  echo -e "${GREEN}运行模型对比实验: ${CLASS_NAME}${NC}"
  python3 experiment_runner.py --modeling-file $MODELING_FILE --output-dir $OUTPUT_DIR --model $MODEL compare --class-name $CLASS_NAME --source-file $SOURCE_FILE --models "gpt-4-turbo" "claude-3-opus"
}

# 批量运行实验
function run_batch_experiment {
  if [ $# -eq 0 ]; then
    echo -e "${RED}错误: 未指定实验类型${NC}"
    exit 1
  fi
  
  EXPERIMENT_TYPE=$1
  CONFIG_FILE="experiment_config.json"
  
  # 对于模型对比实验，使用不同的配置文件
  if [ "$EXPERIMENT_TYPE" == "model_comparison" ]; then
    CONFIG_FILE="model_comparison_config.json"
  fi
  
  echo -e "${GREEN}批量运行${EXPERIMENT_TYPE}实验${NC}"
  python3 experiment_runner.py --modeling-file $MODELING_FILE --output-dir $OUTPUT_DIR --model $MODEL batch --experiment-type $EXPERIMENT_TYPE --config-file $CONFIG_FILE
}

# 运行所有实验
function run_all_experiments {
  echo -e "${GREEN}运行所有实验${NC}"
  
  # 批量运行依赖注入实验
  echo -e "${YELLOW}批量运行依赖注入实验...${NC}"
  run_batch_experiment di
  
  # 批量运行AOP实验
  echo -e "${YELLOW}批量运行AOP切面实验...${NC}"
  run_batch_experiment aop
  
  # 批量运行完整代码还原实验
  echo -e "${YELLOW}批量运行完整代码还原实验...${NC}"
  run_batch_experiment complete
  
  # 批量运行模型对比实验
  echo -e "${YELLOW}批量运行模型对比实验...${NC}"
  run_batch_experiment model_comparison
  
  echo -e "${GREEN}所有实验已完成!${NC}"
}

# 根据命令执行相应的实验
case $COMMAND in
  di)
    run_di_experiment
    ;;
  aop)
    run_aop_experiment
    ;;
  complete)
    run_complete_experiment
    ;;
  compare)
    run_compare_experiment
    ;;
  batch)
    if [ $# -eq 0 ]; then
      echo -e "${RED}错误: 未指定实验类型${NC}"
      print_help
      exit 1
    fi
    run_batch_experiment $1
    ;;
  all)
    run_all_experiments
    ;;
  *)
    echo -e "${RED}错误: 未知命令 $COMMAND${NC}"
    print_help
    exit 1
    ;;
esac

echo -e "${GREEN}实验完成!${NC}" 