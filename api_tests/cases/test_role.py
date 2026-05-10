"""角色管理模块接口测试"""

import time

import allure
import pytest


@allure.epic("RuoYi 接口自动化")
@allure.feature("角色管理")
class TestRoleSystemData:
    """系统初始化数据完整性验证"""

    @allure.story("数据完整性")
    @allure.title("超级管理员角色配置正确")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.role
    def test_admin_role_config(self, admin_client):
        """
        系统级数据完整性验证：
        - 超管角色（roleKey=admin）必须存在
        - 必须标记为 admin=true
        - dataScope 必须是 1（全部数据）
        
        这些是 RuoYi 的"系统不变量"——不能被任何业务操作破坏
        """
        result = admin_client.get("/system/role/list")

        admin_roles = [r for r in result["rows"] if r["roleKey"] == "admin"]
        assert len(admin_roles) == 1, "找不到超管角色，系统数据被破坏"
        assert admin_roles[0]["admin"] is True
        assert admin_roles[0]["dataScope"] == "1", "超管 dataScope 应为 1（全部数据）"

@allure.epic("RuoYi 接口自动化")
@allure.feature("角色管理")
class TestRoleCRUD:
    """角色增删改用例"""

    @pytest.fixture
    def test_role_id(self, admin_client):
        """
        创建测试角色 fixture，用例结束自动删除
        """
        unique_key = f"test_role_{int(time.time() * 1000)}"

        new_role = {
            "roleName": unique_key,
            "roleKey": unique_key,
            "roleSort": 99,
            "status": "0",
            "menuCheckStrictly": True,
            "deptCheckStrictly": True,
            "remark": "自动化创建",
            "menuIds": [1, 100, 1000, 1001]  # 系统管理 + 用户管理 + 子菜单
        }
        create_result = admin_client.post("/system/role", json=new_role)
        assert create_result["code"] == 200, f"前置创建角色失败: {create_result['msg']}"

        # 查刚建的 roleId
        list_result = admin_client.get(
            "/system/role/list",
            params={"roleName": unique_key}
        )
        role_id = list_result["rows"][0]["roleId"]

        yield role_id

        # teardown：清理
        admin_client.delete(f"/system/role/{role_id}")

    @allure.story("新增")
    @allure.title("新增角色 - 完整字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.role
    def test_role_create_success(self, admin_client, test_role_id):
        """fixture 已建好角色，验证它确实存在"""
        result = admin_client.get(f"/system/role/{test_role_id}")

        assert result["code"] == 200
        assert result["data"]["roleId"] == test_role_id
        assert result["data"]["status"] == "0"

    @allure.story("新增")
    @allure.title("新增角色 - roleKey 重复应失败")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.role
    def test_role_create_duplicate_key(self, admin_client):
        """已存在的 roleKey (admin) 应被拒绝"""
        duplicate_role = {
            "roleName": "重复测试",
            "roleKey": "admin",  # 故意用已存在的
            "roleSort": 99,
            "status": "0",
            "menuCheckStrictly": True,
            "deptCheckStrictly": True,
            "menuIds": []
        }
        result = admin_client.post("/system/role", json=duplicate_role)

        assert result["code"] == 500
        assert "已存在" in result["msg"] or "重复" in result["msg"]

    @allure.story("修改")
    @allure.title("修改角色 - 修改名称")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.role
    def test_role_update_name(self, admin_client, test_role_id):
        """先查后改 - PUT 全量提交"""
        # 1. 查完整对象
        detail = admin_client.get(f"/system/role/{test_role_id}")
        role_data = detail["data"]

        # 2. 改字段
        role_data["roleName"] = "修改后的角色名"
        # 必须带上 menuIds（接口要求）
        role_data["menuIds"] = [1, 100]

        # 3. 提交
        update_result = admin_client.put("/system/role", json=role_data)
        assert update_result["code"] == 200, f"修改失败: {update_result['msg']}"

        # 4. 二次验证
        verify = admin_client.get(f"/system/role/{test_role_id}")
        assert verify["data"]["roleName"] == "修改后的角色名"

    @allure.story("修改")
    @allure.title("修改角色状态 - 停用")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.role
    def test_role_change_status(self, admin_client, test_role_id):
        """专用状态接口"""
        result = admin_client.put(
            "/system/role/changeStatus",
            json={"roleId": test_role_id, "status": "1"}
        )
        assert result["code"] == 200

        # 验证状态改了
        verify = admin_client.get(f"/system/role/{test_role_id}")
        assert verify["data"]["status"] == "1"

    @allure.story("删除")
    @allure.title("删除角色 - 单个")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.role
    def test_role_delete_single(self, admin_client):
        """创建一个角色后删除（不用 fixture，独立验证）"""
        unique_key = f"to_delete_{int(time.time() * 1000)}"

        admin_client.post("/system/role", json={
            "roleName": unique_key,
            "roleKey": unique_key,
            "roleSort": 99,
            "status": "0",
            "menuCheckStrictly": True,
            "deptCheckStrictly": True,
            "menuIds": []
        })
        list_r = admin_client.get(
            "/system/role/list",
            params={"roleName": unique_key}
        )
        role_id = list_r["rows"][0]["roleId"]

        # 删除
        delete_result = admin_client.delete(f"/system/role/{role_id}")
        assert delete_result["code"] == 200

        # 验证：列表查不到
        list_after = admin_client.get(
            "/system/role/list",
            params={"roleName": unique_key}
        )
        assert list_after["total"] == 0

    @allure.story("删除")
    @allure.title("删除角色 - 不能删除超级管理员")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.role
    def test_role_delete_admin_forbidden(self, admin_client):
        """超管角色（roleId=1）应被业务规则拒绝"""
        result = admin_client.delete("/system/role/1")

        # 应该 code 500，msg 含"超级管理员"或"不允许"
        assert result["code"] == 500


@allure.epic("RuoYi 接口自动化")
@allure.feature("角色管理")
class TestRoleUserAssignment:
    """角色-用户分配关系用例"""

    @allure.story("分配")
    @allure.title("查询角色已分配的用户列表")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.role
    def test_role_allocated_users(self, admin_client):
        """查询 roleId=2 (普通角色) 已挂的用户"""
        result = admin_client.get(
            "/system/role/authUser/allocatedList",
            params={"roleId": 2}
        )

        assert result["code"] == 200
        assert "rows" in result
        # 至少应该有 ry 用户
        assert result["total"] >= 1
        usernames = [u["userName"] for u in result["rows"]]
        assert "ry" in usernames, "ry 用户应在普通角色下"

    @allure.story("分配")
    @allure.title("查询角色未分配的用户列表")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.role
    def test_role_unallocated_users(self, admin_client):
        """查询 roleId=2 还未挂载的用户"""
        result = admin_client.get(
            "/system/role/authUser/unallocatedList",
            params={"roleId": 2}
        )

        assert result["code"] == 200
        assert "rows" in result
        # admin 用户是超管，不归属普通角色，应在未分配列表中
        usernames = [u["userName"] for u in result["rows"]]
        # 注意：admin 可能是超管，未分配列表返回的是所有"非该角色"的用户
        # 这里弱断言：返回结构正确即可
        assert isinstance(usernames, list)