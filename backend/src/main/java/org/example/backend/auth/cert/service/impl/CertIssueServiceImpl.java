package org.example.backend.auth.cert.service.impl;

import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.asn1.x509.BasicConstraints;
import org.bouncycastle.asn1.x509.Extension;
import org.bouncycastle.asn1.x509.KeyPurposeId;
import org.bouncycastle.asn1.x509.KeyUsage;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;
import org.example.backend.auth.cert.config.CertProperties;
import org.example.backend.auth.cert.constant.CertConstants;
import org.example.backend.auth.cert.entity.SysCertApplyEntity;
import org.example.backend.auth.cert.entity.SysUserCertEntity;
import org.example.backend.auth.cert.mapper.SysUserCertMapper;
import org.example.backend.auth.cert.service.CertIssueService;
import org.example.backend.auth.cert.util.CertPathUtils;
import org.example.backend.auth.cert.util.X509CertUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.PostConstruct;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.file.Paths;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.SecureRandom;
import java.security.Security;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.Date;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Service
public class CertIssueServiceImpl implements CertIssueService {

    private static final Logger log = LoggerFactory.getLogger(CertIssueServiceImpl.class);

    static {
        if (Security.getProvider(BouncyCastleProvider.PROVIDER_NAME) == null) {
            Security.addProvider(new BouncyCastleProvider());
        }
    }

    @Autowired
    private CertProperties certProperties;

    @Autowired
    private CertPathUtils certPathUtils;

    @Autowired
    private SysUserCertMapper sysUserCertMapper;

    private X509Certificate caCert;
    private PrivateKey caPrivateKey;

    @PostConstruct
    // 加载中间CA证书与私钥
    public void loadCaMaterial() {
        if (!StringUtils.hasText(certProperties.getIntermediateCert())
                || !StringUtils.hasText(certProperties.getIntermediateKey())) {
            log.warn("未配置 cert.intermediate-cert / intermediate-key，证书签发功能不可用");
            return;
        }
        Path certPath = Paths.get(certProperties.getIntermediateCert());
        Path keyPath = Paths.get(certProperties.getIntermediateKey());
        if (!Files.isRegularFile(certPath) || !Files.isRegularFile(keyPath)) {
            log.warn("中间 CA 文件不存在（cert={}, key={}），证书签发功能不可用；"
                            + "审批签发前请配置正确路径",
                    certPath, keyPath);
            return;
        }
        try (InputStream in = Files.newInputStream(certPath)) {
            caCert = (X509Certificate) java.security.cert.CertificateFactory.getInstance("X.509")
                    .generateCertificate(in);
        } catch (Exception e) {
            throw new IllegalStateException("加载中间 CA 证书失败: " + certPath, e);
        }
        try {
            byte[] keyBytes = Files.readAllBytes(keyPath);
            String pem = new String(keyBytes, StandardCharsets.UTF_8);
            caPrivateKey = readPrivateKeyPem(pem);
        } catch (Exception e) {
            throw new IllegalStateException("加载中间 CA 私钥失败: " + keyPath, e);
        }
        log.info("中间 CA 已加载: {}", certPath);
    }

    @Override
    // 为申请签发签名证与加密证并打包
    public String issueForApply(SysCertApplyEntity apply, String subjectCn, String subjectO, String subjectOu,
                               int validDays) {
        if (caCert == null || caPrivateKey == null) {
            throw new IllegalStateException("中间 CA 未加载，请检查 cert.intermediate-cert / intermediate-key 配置");
        }
        try {
            Path dir = certPathUtils.ensureApplyDir(apply.getUserId(), apply.getApplyId());
            String p12Password = randomPassword(certProperties.getP12PasswordLength());
            X500Name subject = buildSubject(subjectCn, subjectO, subjectOu);
            // 使用 CA 证书 Subject 的 DER 编码，保证 issuer DN 顺序与 nginx Acceptable CA 一致（Chrome 据此筛选客户端证）
            X500Name issuer = X500Name.getInstance(caCert.getSubjectX500Principal().getEncoded());

            IssuedPair signPair = issueOne(dir, "sign", subject, issuer, validDays, true);
            IssuedPair encryptPair = issueOne(dir, "encrypt", subject, issuer, validDays, false);

            exportP12(dir.resolve("sign.p12"), signPair, p12Password, "personalDemo-sign");
            exportP12(dir.resolve("encrypt.p12"), encryptPair, p12Password, "personalDemo-encrypt");

            Path bundle = dir.resolve("bundle.zip");
            writeBundle(bundle, dir);

            persistUserCert(apply, signPair, CertConstants.CERT_TYPE_SIGN);
            persistUserCert(apply, encryptPair, CertConstants.CERT_TYPE_ENCRYPT);

            apply.setBundlePath(certPathUtils.relativePath(bundle));
            return p12Password;
        } catch (Exception e) {
            throw new RuntimeException("证书签发失败: " + e.getMessage(), e);
        }
    }

    @Override
    // 吊销用户全部有效证书
    public void revokeUserActiveCerts(Long userId) {
        com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<SysUserCertEntity> wrapper =
                new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<>();
        wrapper.eq(SysUserCertEntity::getUserId, userId)
                .eq(SysUserCertEntity::getStatus, CertConstants.CERT_STATUS_ACTIVE)
                .set(SysUserCertEntity::getStatus, CertConstants.CERT_STATUS_REVOKED);
        sysUserCertMapper.update(null, wrapper);
    }

    // 签发单张证书并写入文件
    private IssuedPair issueOne(Path dir, String prefix, X500Name subject, X500Name issuer, int validDays,
                                boolean signCert) throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA", BouncyCastleProvider.PROVIDER_NAME);
        kpg.initialize(2048, new SecureRandom());
        KeyPair keyPair = kpg.generateKeyPair();

        Date notBefore = new Date();
        Date notAfter = new Date(notBefore.getTime() + (long) validDays * 86400000L);
        BigInteger serial = new BigInteger(160, new SecureRandom());

        X509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
                issuer, serial, notBefore, notAfter, subject, keyPair.getPublic());
        if (signCert) {
            builder.addExtension(Extension.basicConstraints, true, new BasicConstraints(false));
            builder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.digitalSignature | KeyUsage.nonRepudiation));
            builder.addExtension(Extension.extendedKeyUsage, false,
                    new org.bouncycastle.asn1.x509.ExtendedKeyUsage(KeyPurposeId.id_kp_clientAuth));
        } else {
            builder.addExtension(Extension.basicConstraints, true, new BasicConstraints(false));
            builder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.keyEncipherment | KeyUsage.dataEncipherment));
        }

        ContentSigner signer = new JcaContentSignerBuilder("SHA256WithRSA")
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .build(caPrivateKey);
        X509CertificateHolder holder = builder.build(signer);
        X509Certificate cert = new JcaX509CertificateConverter()
                .setProvider(BouncyCastleProvider.PROVIDER_NAME)
                .getCertificate(holder);

        Path keyPath = dir.resolve(prefix + ".key");
        Path certPath = dir.resolve(prefix + ".crt");
        Files.write(keyPath, keyPair.getPrivate().getEncoded());
        Files.write(certPath, cert.getEncoded());

        IssuedPair pair = new IssuedPair();
        pair.keyPair = keyPair;
        pair.certificate = cert;
        pair.keyPath = certPathUtils.relativePath(keyPath);
        pair.certPath = certPathUtils.relativePath(certPath);
        pair.p12Path = certPathUtils.relativePath(dir.resolve(prefix + ".p12"));
        pair.fingerprint = X509CertUtils.fingerprintSha256(cert);
        pair.serial = cert.getSerialNumber().toString(16).toUpperCase();
        pair.subjectDn = cert.getSubjectX500Principal().getName();
        pair.issuerDn = cert.getIssuerX500Principal().getName();
        pair.notBefore = notBefore;
        pair.notAfter = notAfter;
        return pair;
    }

    // 导出证书与私钥为P12文件
    private void exportP12(Path p12Path, IssuedPair pair, String password, String alias) throws Exception {
        KeyStore store = KeyStore.getInstance("PKCS12", BouncyCastleProvider.PROVIDER_NAME);
        store.load(null, null);
        store.setKeyEntry(alias, pair.keyPair.getPrivate(), password.toCharArray(),
                new Certificate[]{pair.certificate, caCert});
        try (FileOutputStream out = new FileOutputStream(p12Path.toFile())) {
            store.store(out, password.toCharArray());
        }
    }

    // 打包证书文件为ZIP
    private void writeBundle(Path bundle, Path dir) throws Exception {
        Path rootCa = resolveRootCertPath();
        Path intermediateCa = Paths.get(certProperties.getIntermediateCert());
        if (!Files.isRegularFile(rootCa)) {
            throw new IllegalStateException("根 CA 证书不存在: " + rootCa);
        }
        if (!Files.isRegularFile(intermediateCa)) {
            throw new IllegalStateException("中间 CA 证书不存在: " + intermediateCa);
        }

        byte[] readme = buildReadme().getBytes(StandardCharsets.UTF_8);
        try (ZipOutputStream zos = new ZipOutputStream(new FileOutputStream(bundle.toFile()))) {
            addToZip(zos, rootCa, "root-ca.crt");
            addToZip(zos, intermediateCa, "intermediate-ca.crt");
            addToZip(zos, dir.resolve("sign.p12"), "sign.p12");
            addToZip(zos, dir.resolve("encrypt.p12"), "encrypt.p12");
            ZipEntry entry = new ZipEntry("README.txt");
            zos.putNextEntry(entry);
            zos.write(readme);
            zos.closeEntry();
        }
    }

    // 解析根CA证书路径
    private Path resolveRootCertPath() {
        if (StringUtils.hasText(certProperties.getRootCert())) {
            return Paths.get(certProperties.getRootCert());
        }
        Path intermediate = Paths.get(certProperties.getIntermediateCert());
        return intermediate.getParent().getParent().resolve("root/root-ca.crt");
    }

    // 将文件添加到ZIP包
    private void addToZip(ZipOutputStream zos, Path file, String entryName) throws Exception {
        ZipEntry entry = new ZipEntry(entryName);
        zos.putNextEntry(entry);
        zos.write(Files.readAllBytes(file));
        zos.closeEntry();
    }

    // 生成证书包说明文档内容
    private String buildReadme() {
        return "personalDemo 客户端证书包\n\n"
                + "1. root-ca.crt → 导入系统/浏览器「受信任的根证书颁发机构」\n"
                + "2. intermediate-ca.crt → 导入「中间证书颁发机构」\n"
                + "3. sign.p12、encrypt.p12 → 双击导入「个人」证书存储（须显示「有对应的私钥」）\n"
                + "4. P12 密码请在平台「我的证书」页查看（仅展示一次，本包内不包含密码）\n"
                + "5. 证书登录仅使用 sign 证；HTTPS 自测: https://你的站点:8443/debug-cert\n"
                + "6. 登录页点击「证书登录」\n";
    }

    // 持久化用户证书记录
    private void persistUserCert(SysCertApplyEntity apply, IssuedPair pair, String certType) {
        SysUserCertEntity entity = new SysUserCertEntity();
        entity.setUserId(apply.getUserId());
        entity.setApplyId(apply.getApplyId());
        entity.setCertType(certType);
        entity.setCertFingerprint(pair.fingerprint);
        entity.setCertSerial(pair.serial);
        entity.setSubjectDn(pair.subjectDn);
        entity.setIssuerDn(pair.issuerDn);
        entity.setNotBefore(pair.notBefore);
        entity.setNotAfter(pair.notAfter);
        entity.setCertPath(pair.certPath);
        entity.setKeyPath(pair.keyPath);
        entity.setP12Path(pair.p12Path);
        entity.setStatus(CertConstants.CERT_STATUS_ACTIVE);
        entity.setCreateTime(new Date());
        sysUserCertMapper.insert(entity);
    }

    // 构建证书主题DN
    private X500Name buildSubject(String cn, String o, String ou) {
        StringBuilder sb = new StringBuilder("CN=").append(cn);
        if (StringUtils.hasText(ou)) {
            sb.append(",OU=").append(ou);
        }
        if (StringUtils.hasText(o)) {
            sb.append(",O=").append(o);
        }
        sb.append(",C=CN");
        return new X500Name(sb.toString());
    }

    // 生成随机P12密码
    private String randomPassword(int length) {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
        SecureRandom random = new SecureRandom();
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }

    // 从PEM格式解析私钥
    private PrivateKey readPrivateKeyPem(String pem) throws Exception {
        org.bouncycastle.openssl.PEMParser parser =
                new org.bouncycastle.openssl.PEMParser(new java.io.StringReader(pem));
        Object obj = parser.readObject();
        parser.close();
        org.bouncycastle.openssl.jcajce.JcaPEMKeyConverter converter =
                new org.bouncycastle.openssl.jcajce.JcaPEMKeyConverter()
                        .setProvider(BouncyCastleProvider.PROVIDER_NAME);
        if (obj instanceof org.bouncycastle.openssl.PEMKeyPair) {
            return converter.getPrivateKey(((org.bouncycastle.openssl.PEMKeyPair) obj).getPrivateKeyInfo());
        }
        if (obj instanceof org.bouncycastle.asn1.pkcs.PrivateKeyInfo) {
            return converter.getPrivateKey((org.bouncycastle.asn1.pkcs.PrivateKeyInfo) obj);
        }
        throw new IllegalArgumentException("无法解析中间 CA 私钥");
    }

    private static class IssuedPair {
        private KeyPair keyPair;
        private X509Certificate certificate;
        private String fingerprint;
        private String serial;
        private String subjectDn;
        private String issuerDn;
        private Date notBefore;
        private Date notAfter;
        private String certPath;
        private String keyPath;
        private String p12Path;
    }
}
