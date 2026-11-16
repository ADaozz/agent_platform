#!/usr/bin/env bash
# 构建可发布产物（在仓库根目录执行，普通用户即可）：
#   backend.jar + 前端 dist + agent-runtime 源码 + 版本信息
#
#   deploy/scripts/build-release.sh [输出目录]   # 默认 ./build
#
# 产物：<输出目录>/release-<版本>/ 与同名 .tar.gz，交给 release.sh 部署。
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT_DIR=${1:-$REPO_ROOT/build}
GIT_SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)
VERSION=$(date +%Y%m%d-%H%M%S)-$GIT_SHA
STAGE="$OUT_DIR/release-$VERSION"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

for c in mvn java npm rsync tar; do
  command -v "$c" >/dev/null 2>&1 || die "缺少命令：$c"
done

# 后端：java.version=1.8，Lombok 1.18.24 在 JDK 21+ 上无法编译，推荐直接用 JDK 8
JAVA_MAJOR=$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\)\..*/\1/p' | head -1)
[ -n "$JAVA_MAJOR" ] || die "无法识别 java 版本"
[ "$JAVA_MAJOR" = 1 ] && JAVA_MAJOR=$(java -version 2>&1 | sed -n 's/.*version "1\.\([0-9]*\).*/\1/p' | head -1)
[ "${JAVA_MAJOR:-0}" -le 20 ] || die "JDK $JAVA_MAJOR 无法编译本项目（Lombok 1.18.24 不支持 21+），请用 JDK 8"

log "1/4 构建后端（mvn package，JDK $JAVA_MAJOR）"
# 用 maven.test.skip 而不是 skipTests：src/test 里有 Set.of() 等 Java 9+ API，
# 在 JDK 8 下连测试编译都会失败。
mvn -B -q -f "$REPO_ROOT/backend/pom.xml" -Dmaven.test.skip=true package
JAR=$(ls "$REPO_ROOT"/backend/target/*.jar 2>/dev/null | grep -v '\.original$' | head -1 || true)
[ -n "$JAR" ] || die "没有找到后端 jar"
printf '    %s\n' "$(basename "$JAR")"

log "2/4 构建前端（type-check + vite build）"
# node_modules 已存在且不比 lockfile 旧时跳过安装，避免每次都重下 350MB
if [ -d "$REPO_ROOT/frontEnd/node_modules" ] && \
   [ -z "$(find "$REPO_ROOT/frontEnd/package-lock.json" -newer "$REPO_ROOT/frontEnd/node_modules" 2>/dev/null)" ]; then
  printf '    复用现有 node_modules\n'
else
  npm ci --prefix "$REPO_ROOT/frontEnd" --silent
fi
npm run build --prefix "$REPO_ROOT/frontEnd"
[ -d "$REPO_ROOT/frontEnd/dist" ] || die "前端构建产物 frontEnd/dist 不存在"
ALT_DIST=0
if [ ! -f "$REPO_ROOT/frontEnd/dist/index.html" ]; then
  # vite 默认输出到 dist；如果项目改成 dist/<子目录>，这里兜底
  FOUND=$(find "$REPO_ROOT/frontEnd/dist" -maxdepth 2 -name index.html | head -1)
  [ -n "$FOUND" ] || die "dist 里没有 index.html"
  ALT_DIST=1
fi

log "3/4 组装发布目录"
rm -rf "$STAGE"
install -d "$STAGE/frontend"
install -m 644 "$JAR" "$STAGE/backend.jar"
if [ "$ALT_DIST" = 1 ]; then
  rsync -a "$(dirname "$FOUND")/" "$STAGE/frontend/"
else
  rsync -a "$REPO_ROOT/frontEnd/dist/" "$STAGE/frontend/"
fi

# agent-runtime：只要运行需要的源码与 Skill，跳过本地虚拟环境与数据
rsync -a \
  --exclude '.venv/' \
  --exclude '.platform*/' \
  --exclude '__pycache__/' \
  --exclude 'tests/' \
  --exclude '*.pyc' \
  "$REPO_ROOT/agent-runtime/" "$STAGE/runtime/"

cat >"$STAGE/RELEASE" <<EOF
version=$VERSION
git_sha=$GIT_SHA
built_at=$(date -Is)
built_by=$(id -un)@$(hostname)
EOF

log "4/4 打包"
tar -C "$OUT_DIR" -czf "$STAGE.tar.gz" "release-$VERSION"

log "完成"
cat <<EOF
    目录：$STAGE
    压缩包：$STAGE.tar.gz
    大小：$(du -sh "$STAGE.tar.gz" | cut -f1)

部署到服务器：
    scp $STAGE.tar.gz root@<server>:/tmp/
    ssh root@<server> 'tar -C /tmp -xzf /tmp/release-$VERSION.tar.gz'
    ssh root@<server> 'sudo /opt/agent-platform/deploy/scripts/release.sh /tmp/release-$VERSION'
EOF
