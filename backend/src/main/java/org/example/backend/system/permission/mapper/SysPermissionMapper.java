package org.example.backend.system.permission.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.system.permission.entity.SysPermissionEntity;

import java.util.List;

public interface SysPermissionMapper extends BaseMapper<SysPermissionEntity> {

    @Select("SELECT DISTINCT p.sys_permission " +
            "FROM sys_user_role ur " +
            "JOIN sys_role_permission rp ON ur.role_id = rp.role_id " +
            "JOIN sys_permission p ON rp.permission_id = p.permission_id " +
            "WHERE ur.user_id = #{userId}")
    List<String> selectSysPermissionByUserId(@Param("userId") Long userId);

    @Select("SELECT DISTINCT p.permission_id AS id, p.sys_permission AS label " +
            "FROM sys_user_role ur " +
            "JOIN sys_role_permission rp ON ur.role_id = rp.role_id " +
            "JOIN sys_permission p ON rp.permission_id = p.permission_id " +
            "WHERE ur.user_id = #{userId}")
    List<OptionVO> selectPermissionOptionsByUserId(@Param("userId") Long userId);

    @Select("SELECT permission_id AS id, sys_permission AS label " +
            "FROM sys_permission ORDER BY permission_id")
    List<OptionVO> selectAllPermissionOptions();
}
