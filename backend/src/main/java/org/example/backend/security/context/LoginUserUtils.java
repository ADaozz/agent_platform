package org.example.backend.security.context;

import org.apache.shiro.SecurityUtils;
import org.springframework.stereotype.Service;

@Service
public class LoginUserUtils {
    public static Long getUserId(){
        Object principal = SecurityUtils.getSubject().getPrincipal();
        return principal == null ? null : (Long) principal;
    }
}
