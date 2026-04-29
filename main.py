import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import datetime
import asyncio
from myserver import server_on

# --- Discord Bot Setup ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # ใช้ prefix เดิมไว้เผื่อใช้คำสั่งอื่น แต่ slash command จะทำงานแยกต่างหาก
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # รัน Flask Server
        print("✅ Flask server is online!")
        # อัปเดต Slash Commands ไปยัง Discord
        await self.tree.sync()
        print("✅ Slash commands synced!")

bot = MyBot()
ticket_counter = 1

# --- หน้าต่างกรอกข้อมูล (Modal) สำหรับส่งฟ้อง ---
class FilingModal(ui.Modal, title='ศูนย์รับเรื่อง พระธรรมนูญ (ส่งฟ้อง)'):
    def __init__(self, role_ids):
        super().__init__()
        self.role_ids = role_ids

    u_name = ui.TextInput(label='[ ชื่อบัญชีผู้ฟ้อง | Username ]', placeholder='ชื่อของคุณ...')
    u_rank = ui.TextInput(label='[ ยศผู้ฟ้อง | Rank ]', placeholder='ระบุยศของคุณ...')
    u_branch = ui.TextInput(label='[ สังกัดผู้ฟ้อง | Branch ]', placeholder='ระบุสังกัดของคุณ...')
    accused_info = ui.TextInput(label='[ ข้อมูลผู้กระทำผิด ]', placeholder='ชื่อ | ยศ | สังกัด ของผู้กระทำผิด', style=discord.TextStyle.paragraph)
    description = ui.TextInput(label='[ บรรยายเหตุการณ์ ]', style=discord.TextStyle.paragraph, placeholder='เล่ารายละเอียดเหตุการณ์ที่เกิดขึ้น...')

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_counter
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        current_category = interaction.channel.category
        
        # สิทธิ์พื้นฐาน (คนเปิด + บอท)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
        }
        
        # เพิ่มสิทธิ์ให้ Role ที่ถูกเลือกตอน Setup
        mention_string = ""
        for r_id in self.role_ids:
            role = guild.get_role(r_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
                mention_string += f"{role.mention} "

        try:
            channel_name = f"การส่งฟ้องห้องที่-{ticket_counter}-รอรับเรื่อง"
            channel = await guild.create_text_channel(name=channel_name, category=current_category, overwrites=overwrites)
            ticket_counter += 1
            
            embed = discord.Embed(title="📄 รายละเอียดการส่งฟ้อง", color=discord.Color.red(), timestamp=datetime.datetime.now())
            embed.add_field(name="⚖️ ข้อมูลผู้ฟ้อง", value=f"**ชื่อ:** {self.u_name}\n**ยศ:** {self.u_rank}\n**สังกัด:** {self.u_branch}\n**ดิสคอร์ด:** {interaction.user.mention}", inline=False)
            embed.add_field(name="👤 ข้อมูลผู้กระทำผิด", value=self.accused_info, inline=False)
            embed.add_field(name="📝 รายละเอียด", value=self.description, inline=False)
            embed.set_footer(text="สำนักพระธรรมนูญ")
            
            # โพสต์ฟอร์มพร้อมแท็กตำแหน่ง
            await channel.send(content=f"แจ้งเตือนเจ้าหน้าที่: {mention_string}", embed=embed, view=AdminControlView(ticket_type="filing"))
            await interaction.followup.send(f"✅ สร้างห้องเรียบร้อยแล้วที่ {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}", ephemeral=True)

# --- หน้าต่างกรอกข้อมูล (Modal) สำหรับยื่นอุทธรณ์ ---
class AppealModal(ui.Modal, title='ศูนย์รับเรื่อง พระธรรมนูญ (ยื่นอุทธรณ์)'):
    def __init__(self, role_ids):
        super().__init__()
        self.role_ids = role_ids

    u_name = ui.TextInput(label='[ ชื่อบัญชีผู้ยื่น | Username ]')
    u_rank = ui.TextInput(label='[ ยศผู้ยื่น | Rank ]')
    u_branch = ui.TextInput(label='[ สังกัดผู้ยื่น | Branch ]')
    case_num = ui.TextInput(label='[ หมายเลขคดี | Case number ]')
    statement = ui.TextInput(label='[ คำแถลงของฝ่ายจำเลย ]', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_counter
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        current_category = interaction.channel.category
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
        }
        
        mention_string = ""
        for r_id in self.role_ids:
            role = guild.get_role(r_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
                mention_string += f"{role.mention} "

        try:
            channel_name = f"การยื่นอุทธรณ์ห้องที่-{ticket_counter}-รอรับเรื่อง"
            channel = await guild.create_text_channel(name=channel_name, category=current_category, overwrites=overwrites)
            ticket_counter += 1

            embed = discord.Embed(title="⚖️ รายละเอียดการยื่นอุทธรณ์", color=discord.Color.blue(), timestamp=datetime.datetime.now())
            embed.add_field(name="👤 ข้อมูลผู้ยื่น", value=f"**ชื่อ:** {self.u_name}\n**ยศ:** {self.u_rank}\n**สังกัด:** {self.u_branch}\n**ดิสคอร์ด:** {interaction.user.mention}", inline=False)
            embed.add_field(name="🔢 หมายเลขคดี", value=self.case_num, inline=True)
            embed.add_field(name="💬 คำแถลง", value=self.statement, inline=False)
            embed.set_footer(text="สำนักพระธรรมนูญ")

            await channel.send(content=f"แจ้งเตือนเจ้าหน้าที่: {mention_string}", embed=embed, view=AdminControlView(ticket_type="appeal"))
            await interaction.followup.send(f"✅ สร้างห้องเรียบร้อยแล้วที่ {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}", ephemeral=True)

# --- ปุ่มควบคุมสำหรับ Admin ---
class AdminControlView(ui.View):
    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @ui.button(label="อัปเดตสถานะห้อง", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def update_status(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้น!", ephemeral=True)
        
        if self.ticket_type == "filing":
            status_list = ["รอรับเรื่อง", "รอหมายเรียก", "รอรายงานตัว", "รอไต่สวน", "กำลังไต่สวน", "รอพิจารณาคดี", "ปิดคดี", "ยกฟ้อง", "ยกเลิก"]
        else:
            status_list = ["รอรับเรื่อง", "รอพิจารณา", "ปิดคดี", "ยกเลิก"]

        options = [discord.SelectOption(label=s) for s in status_list]
        select = ui.Select(placeholder="เลือกสถานะใหม่...", options=options)

        async def select_callback(inter: discord.Interaction):
            new_status = select.values[0]
            current_name = inter.channel.name
            parts = current_name.split('-')
            
            try:
                if len(parts) >= 3:
                    new_name = f"{parts[0]}-{parts[1]}-{new_status}"
                    await inter.channel.edit(name=new_name)
                
                embed = discord.Embed(description=f"✅ สถานะคดีถูกอัปเดตเป็น: **{new_status}**", color=discord.Color.green())
                await inter.response.send_message(embed=embed)
            except Exception as e:
                # กันกรณีติดคูลดาวน์ชื่อห้อง
                await inter.response.send_message(f"⚠️ สถานะถูกอัปเดตเป็น **{new_status}** แล้ว (แต่ชื่อห้องยังเปลี่ยนไม่ได้เพราะติดคูลดาวน์)", ephemeral=False)

        select.callback = select_callback
        view = ui.View()
        view.add_item(select)
        await interaction.response.send_message("เลือกสถานะ:", view=view, ephemeral=True)

    @ui.button(label="ปิดห้อง (ลบ)", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_room(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator: return
        await interaction.response.send_message("⚠️ กำลังลบห้องใน 5 วินาที...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- View หน้าแรก (ปุ่มเปิด Ticket) ---
class TicketHomeView(ui.View):
    def __init__(self, role_ids):
        super().__init__(timeout=None)
        self.role_ids = role_ids

    @ui.button(label="🕵‍♂️ แจ้งความ (ส่งฟ้อง)", style=discord.ButtonStyle.danger, custom_id="btn_filing")
    async def filing_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FilingModal(role_ids=self.role_ids))

    @ui.button(label="🕵‍♀️ ยื่นอุทธรณ์", style=discord.ButtonStyle.primary, custom_id="btn_appeal")
    async def appeal_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AppealModal(role_ids=self.role_ids))

# --- View สำหรับ Setup (เลือก Role) ---
class SetupRoleView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.selected_roles = []

    @ui.select(cls=ui.RoleSelect, placeholder="เลือกตำแหน่งที่จะให้เห็นห้องและถูกแท็ก...", min_values=1, max_values=5)
    async def role_select(self, interaction: discord.Interaction, select: ui.RoleSelect):
        self.selected_roles = [role.id for role in select.values]
        await interaction.response.send_message(f"✅ เลือกเสร็จสิ้น! ระบบกำลังสร้างแผงควบคุม...", ephemeral=True)
        
        embed = discord.Embed(
            title="🏛 ศูนย์รับเรื่อง พระธรรมนูญ",
            description=(
                "โปรดเลือกหมวดหมู่ที่ตรงกับเรื่องของคุณ เพื่อให้เจ้าหน้าที่สามารถช่วยเหลือคุณได้อย่างรวดเร็ว!\n\n"
                "**🕵‍♂️ หมวดหมู่ที่ 1: แจ้งความ (ส่งฟ้อง)**\n"
                "**🕵‍♂️ หมวดหมู่ที่ 2: ยื่นอุทธรณ์ (ยื่นอุทธรณ์เพื่อลดโทษ)**\n\n"
                "**กดปุ่มด้านล่างเพื่อเปิด Ticket**\n"
                "⚠️ **ข้อควรปฏิบัติ:** โปรดเปิด Ticket เฉพาะเมื่อมีเรื่องจริง หากเปิดมาเล่นอาจถูกลงโทษ!"
            ),
            color=0xf1c40f
        )
        # โพสต์ลงในช่องที่ใช้คำสั่ง
        await interaction.channel.send(embed=embed, view=TicketHomeView(role_ids=self.selected_roles))
        self.stop()

# --- Slash Command สำหรับ Setup ---
@bot.tree.command(name="setup_ticket", description="ตั้งค่าแผงควบคุม Ticket และระบุยศเจ้าหน้าที่")
@app_commands.default_permissions(administrator=True) # จำกัดให้เฉพาะแอดมินใช้ได้
async def setup_ticket_slash(interaction: discord.Interaction):
    view = SetupRoleView()
    # ให้เฉพาะคนที่พิมพ์คำสั่งเห็นหน้าต่างเลือก Role
    await interaction.response.send_message("⚙️ **ขั้นตอนการตั้งค่า:** โปรดเลือกตำแหน่ง (Role) ที่ต้องการให้ดูแลระบบ Ticket นี้จากเมนูด้านล่าง:", view=view, ephemeral=True)

server_on()

# รันบอท
bot.run(os.getenv('TOKEN'))