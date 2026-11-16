package org.example.backend.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.apache.ibatis.mapping.DatabaseIdProvider;
import org.apache.ibatis.mapping.VendorDatabaseIdProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Properties;

@Configuration
public class MybatisPlusConfig {

    @Value("${spring.datasource.driver-class-name:com.kingbase8.Driver}")
    private String driverClassName;

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        DbType dbType = driverClassName != null && driverClassName.contains("sqlite")
                ? DbType.SQLITE
                : DbType.POSTGRE_SQL;
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(dbType));
        return interceptor;
    }

    /**
     * 内联 SQL 方言标识：Kingbase 存在 sys_user/sys_role 等同名系统 catalog，
     * 手写 SQL 需限定 public schema（见 Mapper 中 ${sch}）；SQLite 无 schema 且日期函数不同。
     */
    @Bean
    public DatabaseIdProvider databaseIdProvider() {
        VendorDatabaseIdProvider provider = new VendorDatabaseIdProvider();
        Properties properties = new Properties();
        properties.setProperty("KingbaseES", "kingbase");
        properties.setProperty("PostgreSQL", "kingbase");
        properties.setProperty("SQLite", "sqlite");
        provider.setProperties(properties);
        return provider;
    }
}
