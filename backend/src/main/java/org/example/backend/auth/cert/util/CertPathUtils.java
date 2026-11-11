package org.example.backend.auth.cert.util;

import org.example.backend.auth.cert.config.CertProperties;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Component
public class CertPathUtils {

    @Autowired
    private CertProperties certProperties;

    public Path applyDir(Long userId, Long applyId) {
        return Paths.get(certProperties.getStorageBasePath(), String.valueOf(userId), String.valueOf(applyId));
    }

    public Path ensureApplyDir(Long userId, Long applyId) throws Exception {
        Path dir = applyDir(userId, applyId);
        Files.createDirectories(dir);
        return dir;
    }

    public File bundleFile(Long userId, Long applyId) {
        return applyDir(userId, applyId).resolve("bundle.zip").toFile();
    }

    public String relativePath(Path absolutePath) {
        Path base = Paths.get(certProperties.getStorageBasePath()).toAbsolutePath().normalize();
        return base.relativize(absolutePath.toAbsolutePath().normalize()).toString().replace('\\', '/');
    }

    public Path resolveStoredPath(String relativePath) {
        return Paths.get(certProperties.getStorageBasePath(), relativePath).normalize();
    }
}
