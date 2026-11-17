package org.example.backend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

@SpringBootApplication
@EnableAspectJAutoProxy(proxyTargetClass = true)
@MapperScan({
        "org.example.backend.system.user.mapper",
        "org.example.backend.system.role.mapper",
        "org.example.backend.system.permission.mapper",
        "org.example.backend.system.menu.mapper",
        "org.example.backend.auth.session.mapper",
        "org.example.backend.auth.cert.mapper",
        "org.example.backend.common.operlog.mapper"
})
public class BackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(BackendApplication.class, args);
    }

}
