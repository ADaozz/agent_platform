package org.example.backend.auth.cert.service;

import javax.servlet.http.HttpServletRequest;

public interface CertLoginService {

    Long resolveUserIdFromRequest(HttpServletRequest request);
}
