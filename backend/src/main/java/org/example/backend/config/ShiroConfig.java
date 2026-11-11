package org.example.backend.config;

import org.apache.shiro.cache.MemoryConstrainedCacheManager;
import org.apache.shiro.mgt.DefaultSessionStorageEvaluator;
import org.apache.shiro.mgt.DefaultSubjectDAO;
import org.apache.shiro.mgt.SecurityManager;
import org.apache.shiro.spring.web.ShiroFilterFactoryBean;
import org.apache.shiro.web.mgt.DefaultWebSecurityManager;
import org.example.backend.security.filter.JwtFilter;
import org.example.backend.security.realm.UserRealm;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.servlet.Filter;
import java.util.LinkedHashMap;
import java.util.Map;

@Configuration
public class ShiroConfig {

    @Bean
    public MemoryConstrainedCacheManager shiroCacheManager() {
        return new MemoryConstrainedCacheManager();
    }

    @Bean
    public DefaultWebSecurityManager securityManager(UserRealm userRealm,
                                                     MemoryConstrainedCacheManager shiroCacheManager) {
        DefaultWebSecurityManager manager = new DefaultWebSecurityManager();
        userRealm.setAuthorizationCachingEnabled(true);
        userRealm.setCacheManager(shiroCacheManager);
        manager.setRealm(userRealm);
        DefaultSubjectDAO subjectDAO = new DefaultSubjectDAO();
        DefaultSessionStorageEvaluator evaluator = new DefaultSessionStorageEvaluator();
        evaluator.setSessionStorageEnabled(false);
        subjectDAO.setSessionStorageEvaluator(evaluator);
        manager.setSubjectDAO(subjectDAO);
        return manager;
    }

    @Bean
    public JwtFilter jwtFilter() {
        return new JwtFilter();
    }

    @Bean
    public ShiroFilterFactoryBean shiroFilterFactoryBean(SecurityManager securityManager, JwtFilter jwtFilter) {
        ShiroFilterFactoryBean bean = new ShiroFilterFactoryBean();
        bean.setSecurityManager(securityManager);
        Map<String, Filter> filters = new LinkedHashMap<>();
        filters.put("jwt", jwtFilter);
        bean.setFilters(filters);
        Map<String, String> chain = new LinkedHashMap<>();
        chain.put("/login", "anon");
        chain.put("/login/cert", "anon");
        chain.put("/login/cert/check", "anon");
        chain.put("/login/cert/debug", "anon");
        chain.put("/**", "jwt");
        bean.setFilterChainDefinitionMap(chain);
        return bean;
    }
}
