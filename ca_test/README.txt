personalDemo 客户端证书包（Windows 测试）

详细踩坑与 Nginx 配置见：backend/docs/DEVELOPMENT.md §17

1. 导入 CA（当前用户）：
   - root-ca.crt        → 受信任的根证书颁发机构
   - intermediate-ca.crt → 中间证书颁发机构
2. 双击 sign.p12 导入 → 个人（须显示「有对应的私钥」）
   - 仅 sign 用于登录；encrypt 不要用于证书登录
3. P12 密码请在平台「我的证书」页查看（仅展示一次；**证书包内不含密码**）
4. Chrome 不弹证书选择框：
   - 双击 chrome-autoselect-cert.reg，重启 Chrome
   - Edge 用 edge-autoselect-cert.reg
5. 8443 无弹窗且直接 400（The SSL certificate error）：
   - 先双击 chrome-autoselect-cert-disable.reg（或 edge 版）关闭自动选证
   - 再手动选择 CN=user 的 sign 证
   - 若仍 400：旧版 sign.p12 的 issuer DN 有误，需管理员重新签发后再导入
6. 443 登录页不请求客户端证；证书登录仅走 8443
7. 重启浏览器
8. 自测：https://你的IP:8443/debug-cert
   - hasCert=true, ok=true 表示浏览器已提交客户端证
   - verify=FAILED:... 是正常的（后端用指纹校验，不要求 SUCCESS）
9. 登录页点击「证书登录」
