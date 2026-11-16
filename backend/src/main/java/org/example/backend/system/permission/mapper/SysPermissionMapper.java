package org.example.backend.system.permission.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.system.permission.entity.SysPermissionEntity;

import java.util.List;

public interface SysPermissionMapper extends BaseMapper<SysPermissionEntity> {

    /** Kingbase 下 sys_permission 等为同名系统 catalog，须限定 public；SQLite 无 schema */
    String SCHEMA_BIND = "<bind name='sch' value=\"_databaseId == 'kingbase' ? 'public.' : ''\"/>";

    @Select("<script>" + SCHEMA_BIND
            + "SELECT DISTINCT p.sys_permission "
            + "FROM ${sch}sys_user_role ur "
            + "JOIN ${sch}sys_role_permission rp ON ur.role_id = rp.role_id "
            + "JOIN ${sch}sys_permission p ON rp.permission_id = p.permission_id "
            + "WHERE ur.user_id = #{userId}"
            + "</script>")
    List<String> selectSysPermissionByUserId(@Param("userId") Long userId);

    @Select("<script>" + SCHEMA_BIND
            + "SELECT DISTINCT p.permission_id AS id, p.sys_permission AS label "
            + "FROM ${sch}sys_user_role ur "
            + "JOIN ${sch}sys_role_permission rp ON ur.role_id = rp.role_id "
            + "JOIN ${sch}sys_permission p ON rp.permission_id = p.permission_id "
            + "WHERE ur.user_id = #{userId}"
            + "</script>")
    List<OptionVO> selectPermissionOptionsByUserId(@Param("userId") Long userId);

    @Select("<script>" + SCHEMA_BIND
            + "SELECT permission_id AS id, sys_permission AS label "
            + "FROM ${sch}sys_permission ORDER BY permission_id"
            + "</script>")
    List<OptionVO> selectAllPermissionOptions();
}
